"""
Parse and transform a simplified query syntax into
MongoDB queries.
"""
__author__ = "Dan Gunter"

## Imports
# Standard library
import copy
from numbers import Number
import re


class BadExpression(Exception):
    """Raised by `query()` if the input is not understood.
    """
    def __init__(self, expr, details=""):
        self.expr = expr
        self.details = details
        Exception.__init__(self, "Bad expression")


# or/and tokens
_TOK_OR = " or "
_TOK_AND = " and "


def to_mongo(qry):
    """Transform a simple query with one or more filter expressions
    into a MongoDB query expression.

    :param qry: Filter expression(s), see function docstring for details.
    :type qry: str or list
    :return: MongoDB query
    :rtype: dict
    :raises: BadExpression, if one of the input expressions cannot be parsed

    Expressions have three parts, called in order ``field``, ``operator``,
    and ``value``.

        - `field` is the name of a field in a MongoDB document
        - `value` is the value to compare against:
            * numeric
            * string, you MUST use 'single' or "double" quotes
            * boolean: true, false
        - `operator` is a comparison operator:
            * inequalities: >, <, =, <=, >=, !=
            * PCRE regular expression: ~
            * data type: int, float, string, or bool
            * exists: boolean (true/false) whether field exists in record
            * size: for array fields, an inequality for the array size, given as
              a suffix to the operator: size>, size<

    Multiple expressions can be a single string, or a list.
    In either case, the form is a "disjunction of conjunctions".

    In the string form:

        * "and" joins expressions into groups
        * "or" joins one or more expression groups

    In the list form:

        * The inner list is a group of "and"ed expressions
        * The outer list "or"s the expression groups together.

    In the string form, parentheses before or after the "or"ed expression
    groups [note: even non-sensical ones like '((('], are ignored.
    So these can be used to clarify the groupings.

    **Examples**

    Two sets of filters, return records where either is true:

    >>> to_mongo('(a > 3 and b = "hello") or (c > 1 and d = "goodbye")')
    {'$or': [{'a': {'$gt': 3}, 'b': 'hello'}, {'c': {'$gt': 1}, 'd': 'goodbye'}]}

    Same as previous, but without parentheses:

    >>> to_mongo('a > 3 and b = "hello" or c > 1 and d = "goodbye"')
    {'$or': [{'a': {'$gt': 3}, 'b': 'hello'}, {'c': {'$gt': 1}, 'd': 'goodbye'}]}

    Same as previous, but using lists rather than "and"/"or":

    >>> to_mongo([['a > 3', 'b = "hello"'], ['c > 1', 'd = "goodbye"']])
    {'$or': [{'a': {'$gt': 3}, 'b': 'hello'}, {'c': {'$gt': 1}, 'd': 'goodbye'}]}
    """
    rev = False     # filters, not constraints
    # special case for empty string/list
    if qry == "" or qry == []:
        return {}
    # break input into groups of filters
    unpar = lambda s: s.strip().strip('()')
    if isinstance(qry, str):
        groups = []
        if _TOK_OR in qry:
            groups = [unpar(g).split(_TOK_AND) for g in qry.split(_TOK_OR)]
        else:
            groups = [unpar(qry).split(_TOK_AND)]
    else:
        if isinstance(qry[0], list) or isinstance(qry[0], tuple):
            groups = qry
        else:
            groups = [qry]
    # generate mongodb queries for each filter group
    filters = []
    for filter_exprs in groups:
        mq = MongoQuery()
        for e in filter_exprs:
            try:
                e = unpar(e)
            except AttributeError:
                raise BadExpression(e, "expected string, got '{t}'".format(t=type(e)))
            try:
                constraint = Constraint(*parse_expr(e))
            except ValueError as err:
                raise BadExpression(e, err)
            clause = MongoClause(constraint, rev=rev)
            mq.add_clause(clause)
        filters.append(mq.to_mongo(rev))
    # combine together filters, or strip down the one filter
    if len(filters) > 1:
        result = {'$or': filters}
    else:
        result = filters[0]
    return result

# To parse a single constraint expression
relation_re = re.compile(r'''\s*
    ([a-zA-Z_.0-9]+(?:/[a-zA-Z_.0-9]+)?)\s*     # Identifier
    (<=?|>=?|!?=|exists|~|                      # Operator (1)
      type|                                     # Operator (1a)
      size[><$]?                                # operator (2)
    )\s*
    ([-]?\d+(?:\.\d+)?|                         # Value: number
        \'[^\']+\'|                             #   single-quoted string
        \"[^"]+\"|                              #   double-quoted string
        [Tt]rue|[Ff]alse|                       #   boolean
        [a-zA-Z_][a-zA-Z_.0-9]*                 # variable name
    )
    \s*''', re.VERBOSE)


def parse_expr(e):
    """Parse a single constraint expression.

    Legal expressions are defined by the regular expression `relation_re`.

    :param e: Expression
    :type e: str
    :return: Tuple of field, operator, and value
    :rtype: tuple
    """
    m = relation_re.match(e)
    if m is None:
        raise ValueError("error parsing expression '{}'".format(e))
    field, op, val = m.groups()
    # Try different types
    try:
        # Integer
        val_int = int(val)
        val = val_int
    except ValueError:
        try:
            # Float
            val_float = float(val)
            val = val_float
        except ValueError:
            try:
                # Boolean
                val = {'true': True, 'false': False}[val.lower()]
            except KeyError:
                # String
                if re.match(r'".*"|\'.*\'', val):
                    # strip quotes from strings
                    val = val[1:-1]
    return field, op, val


class Field(object):
    """Single field in a constraint.
    """

    PICK_SEP = '/'   # embedded syntax for picking subfield

    def __init__(self, name, aliases=None):
        """Create from field name.

        :param name: Field name.
        :type name: str
        :param aliases: Aliases for all fields
        :type aliases: dict
        :raise: ValueError for non-string name
        """
        if not isinstance(name, str):
            raise ValueError('Field name must be a string')
        if aliases is not None:
            name = aliases.get(name, name)
            # assign field name and possible subfield name
        if self.PICK_SEP in name:
            self._name, self._subname = name.split(self.PICK_SEP)
        else:
            self._name, self._subname = name, None

    def has_subfield(self):
        return self._subname is not None

    @property
    def name(self):
        return self._name

    @property
    def full_name(self, sep='.'):
        return sep.join((self._name, self._subname))

    @property
    def sub_name(self):
        return self._subname


class ConstraintOperator(object):
    """Operator in a single constraint.
    """
    SIZE = 'size'
    EXISTS = 'exists'
    TYPE = 'type'
    REGEX = '~'

    # enumeration of size operation modifiers
    SZ_EQ, SZ_GT, SZ_LT, SZ_VAR = 1, 2, 3, 4
    SZ_MAPPING = {'>': SZ_GT, '<': SZ_LT, '$': SZ_VAR}
    SZ_OPS = {SZ_GT: '>', SZ_LT: '<', SZ_EQ: '=', SZ_VAR: '='}

    # logical 'not' of an operator
    OP_NOT = {'>': '<=', '>=': '<', '<': '>=', '<=': '>', '=': '!=', '!=': '=',
              EXISTS: EXISTS, SIZE: SIZE, TYPE: TYPE, REGEX: None}

    # set of valid operations
    VALID_OPS = set(OP_NOT.keys())
    for size_sfx in SZ_MAPPING:
        VALID_OPS.add(SIZE + size_sfx)

    # mapping to python operators, where different, for inequalities
    PY_INEQ = {'=': '=='}

    def __init__(self, op):
        """Create new operator.

        :param op: Operator string
        :type op: str
        :raise: ValueError for bad op
        """
        if not isinstance(op, str) or not op in self.VALID_OPS:
            raise ValueError('bad operation: {}'.format(op))
        self._op = op
        self._set_size_code()
        if self.is_size():
            # strip down to prefix
            self._op = self.SIZE

    def __str__(self):
        return self._op

    @property
    def display_op(self):
        if self.is_size():
            s = self._op + ' ' + self.size_op
        else:
            s = self._op
        return s

    @property
    def size_op(self):
        self._check_size()
        return self.SZ_OPS[self._size_code]

    is_exists = lambda self: self._op == self.EXISTS
    is_eq = lambda self: self._op == '='
    is_neq = lambda self: self._op == '!='
    is_equality = lambda self: self._op in ('=', '!=')
    is_inequality = lambda self: self._op in ('>', '>=', '<', '<=')
    is_size = lambda self: self._size_code is not None
    is_variable = lambda self: self._size_code == self.SZ_VAR
    is_size_lt = lambda self: self._check_size() and self._size_code == self.SZ_LT
    is_size_eq = lambda self: self._check_size() and self._size_code == self.SZ_EQ
    is_size_gt = lambda self: self._check_size() and self._size_code == self.SZ_GT
    is_size_var = lambda self: self._check_size() and self._size_code == self.SZ_VAR
    is_type = lambda self: self._op == self.TYPE
    is_regex = lambda self: self._op == self.REGEX

    def reverse(self):
        orig = self._op
        self._op = self.OP_NOT[self._op]
        if self._op is None:
            raise BadExpression("cannot reverse operator '{}'".format(orig))

    def _check_size(self):
        if self._size_code is None:
            raise RuntimeError('Attempted to fetch size code for non-size operator')
        return True

    def _set_size_code(self):
        """Set the code for a size operation.
        """
        if not self._op.startswith(self.SIZE):
            self._size_code = None
            return

        if len(self._op) == len(self.SIZE):
            self._size_code = self.SZ_EQ
        else:
            suffix = self._op[len(self.SIZE):]
            self._size_code = self.SZ_MAPPING.get(suffix, None)
            if self._size_code is None:
                raise ValueError('invalid "{}" suffix "{}"'.format(self.SIZE, suffix))

    def compare(self, lhs_value, rhs_value):
        """Compare left- and right-size of: value <op> value.

        :param lhs_value: Value to left of operator
        :param rhs_value: Value to right of operator
        :return: True if the comparison is valid
        :rtype: bool
        """
        if self.is_eq():
            # simple {field:value}
            return lhs_value is not None and lhs_value == rhs_value
        if self.is_neq():
            return lhs_value is not None and lhs_value != rhs_value  # XXX: 'or'?
        if self.is_exists():
            if rhs_value:
                return lhs_value is not None
            else:
                return lhs_value is None
        if self.is_size():
            if self.is_size_eq() or self.is_size_var():
                return lhs_value == rhs_value
            if self.is_size_gt():
                return lhs_value > rhs_value
            if self.is_size_lt():
                return lhs_value < rhs_value
            raise RuntimeError('unexpected size operator: {}'.format(self._op))
        if self.is_inequality():
            if not isinstance(lhs_value, Number):
                return False
            py_op = self.PY_INEQ.get(self._op, self._op)
            return eval('{} {} {}'.format(lhs_value, py_op, rhs_value))
        if self.is_type():
            ltype = type(lhs_value)
            if rhs_value is Number:
                return ltype in (int, float)
            elif rhs_value is str:
                return ltype is str
            elif rhs_value is bool:
                return ltype is bool
            return False
        if self.is_regex():
            m = rhs_value.match(lhs_value)
            return m is not None


class Constraint(object):
    """Definition of a single constraint.
    """

    # Convert name of type into Python class
    TYPE_MAPPING = {'number': Number, 'int': Number, 'integer': Number, 'float': Number,
                    'str': str, 'string': str, 'bool': bool, 'boolean': bool}

    def __init__(self, field, operator, value):
        """Create constraint on a field.

        :param field: A constraint field
        :type field: Field or str
        :param operator: A constraint operator
        :type operator: ConstraintOperator or str
        :param value: Target value
        :type value: str, Number
        :raise: ValueError if operator/value combination is illegal, or if
                building a Field or ConstraintOperator instance fails.
        """
        if not isinstance(operator, ConstraintOperator):
            operator = ConstraintOperator(operator)
        if not isinstance(field, Field):
            field = Field(field)
        self.field = field
        self._op = operator
        if self._op.is_inequality() and not isinstance(value, Number):
            raise ValueError('inequality with non-numeric value: {}'.format(value))
        elif self._op.is_type():
            value = value.lower()
            t = self.TYPE_MAPPING.get(value, None)
            if t is None:
                allowed = ', '.join(list(self.TYPE_MAPPING.keys()))
                raise ValueError('value for type, {}, not in ({})'.format(value, allowed))
            self._orig_value, value = value, t
        elif self._op.is_regex():
            if isinstance(value, Number):
                raise ValueError('regular expression with numeric value: {}'.format(value))
            self._orig_value, value = value, re.compile(value)
        self.value = value

    def passes(self, value):
        """Does the given value pass this constraint?

        :return: True,None if so; False,<expected> if not
        :rtype: tuple
        """
        try:
            if self._op.compare(value, self.value):
                return True, None
            else:
                return False, self.value
        except ValueError as err:
            return False, str(err)

    @property
    def op(self):
        """Constraint operator
        :return: The operator
        :rtype: ConstraintOperator
        """
        return self._op

    def __str__(self):
        return '{} {}'.format(self.field.name, self._op)


class ConstraintGroup(object):
    """Definition of a group of constraints, for a given field.
    """

    def __init__(self, field=None):
        """

        :param field: The field to which all constraints apply
        :type field: Field (cannot be None)
        """
        assert (field is not None)
        self.constraints = []
        self._existence_constraints = []
        self._array, self._range = False, False
        self._field = field

    def add_constraint(self, op, val):
        """Add new constraint.

        :param op: Constraint operator
        :type op: ConstraintOperator
        :param val: Constraint value
        :type val: str,Number
        :raise: ValueError if combination of constraints is illegal
        """
        if len(self.constraints) > 0:
            if op.is_equality():
                clist = ', '.join(map(str, self.constraints))
                raise ValueError('Field {}: equality operator cannot be combined '
                                 'with others: {}'.format(self._field.name, clist))
            elif op.is_exists():
                raise ValueError('Field {}: existence is implied '
                                 'by other operators'.format(self._field.name))
        constraint = Constraint(self._field, op, val)
        self.constraints.append(constraint)
        if self._field.has_subfield():
            self._array = True
        elif op.is_inequality():
            self._range = True

    def has_array(self):
        return self._array

    def get_conflicts(self):
        """Get conflicts in constraints, if any.

        :return: Description of each conflict, empty if none.
        :rtype: list(str)
        """
        conflicts = []
        if self._array and self._range:
            conflicts.append('cannot use range expressions on arrays')
        return conflicts

    def add_existence(self, rev):
        """Add existence constraint for the field.

        This is necessary because the normal meaning of 'x > 0' is: x > 0 and is present.
        Without the existence constraint, MongoDB will treat 'x > 0' as: 'x' > 0 *or* is absent.
        Of course, if the constraint is already about existence, nothing is done.

        :rtype: None
        """
        if len(self.constraints) == 1 and (
            # both 'exists' and strict equality don't require the extra clause
            self.constraints[0].op.is_exists() or
                self.constraints[0].op.is_equality()):
            return
        value = not rev   # value is False if reversed, otherwise True
        constraint = Constraint(self._field, ConstraintOperator.EXISTS, value)
        self._existence_constraints.append(constraint)

    @property
    def existence_constraints(self):
        return self._existence_constraints

    def __iter__(self):
        return iter(self.constraints)


class MongoClause(object):
    """Representation of query clause in a MongoDB query.
       Ho, Ho, Ho! Merry Mongxmas!
    """
    # Target location, main part of query or where-clauses
    LOC_MAIN, LOC_WHERE, LOC_MAIN2 = 0, 1, 2

    # Mongo versions of operations
    MONGO_OPS = {
        '>': '$gt', '>=': '$gte',
        '<': '$lt', '<=': '$lte',
        ConstraintOperator.EXISTS: '$exists',
        ConstraintOperator.SIZE: '$size',
        ConstraintOperator.TYPE: '$type',
        ConstraintOperator.REGEX: '$regex',
        '!=': '$ne', '=': None
    }

    # Javascript version of operations, for $where clauses
    JS_OPS = {'=': '=='}  # only different ones need to be here

    # Reverse-mapping of operations
    MONGO_OPS_REV = {v: k for k, v in MONGO_OPS.items()
                     if v is not None}

    # Map of Python types to Javascript type names
    JS_TYPES = {Number: 'number', str: 'string', bool: 'boolean'}

    def __init__(self, constraint, rev=True, exists_main=False):
        """Create new clause from a constraint.

        :param constraint: The constraint
        :type constraint: Constraint
        :param rev: Whether to reverse the sense of the constraint, i.e. in order
        to select records that do not meet it.
        :type rev: bool
        :param exists_main: Put exists into main clause
        :type exists_main: bool
        :raise: AssertionError if constraint is None

        """
        assert constraint is not None
        self._rev = rev
        self._loc, self._expr = self._create(constraint, exists_main)
        self._constraint = constraint

    @property
    def query_loc(self):
        """Where this clause should go in the query.
        The two possible values are enumerated by variables in this class:

        - MongoClause.LOC_MAIN
        - MongoClause.LOC_WHERE

        :return: Location code
        :rtype: int
        """
        return self._loc

    @property
    def expr(self):
        """Query expression
        """
        return self._expr

    @property
    def constraint(self):
        return self._constraint

    def _create(self, constraint, exists_main):
        """Create MongoDB query clause for a constraint.

        :param constraint: The constraint
        :type constraint: Constraint
        :param exists_main: Put exists into main clause
        :type exists_main: bool
        :return: New clause
        :rtype: MongoClause
        :raise: ValueError if value doesn't make sense for operator
        """
        c = constraint  # alias
        op = self._reverse_operator(c.op) if self._rev else c.op
        mop = self._mongo_op_str(op)
        # build the clause parts: location and expression
        loc = MongoClause.LOC_MAIN  # default location
        if op.is_exists():
            loc = MongoClause.LOC_MAIN2 if exists_main else MongoClause.LOC_MAIN
            assert (isinstance(c.value, bool))
            # for exists, reverse the value instead of the operator
            not_c_val = not c.value if self._rev else c.value
            expr = {c.field.name: {mop: not_c_val}}
        elif op.is_size():
            if op.is_variable():
                # variables only support equality, and need to be in $where
                loc = MongoClause.LOC_WHERE
                js_op = '!=' if self._rev else '=='
                expr = 'this.{}.length {} this.{}'.format(c.field.name, js_op, c.value)
            elif op.is_size_eq() and not self._rev:
                expr = {c.field.name: {'$size': c.value}}
            else:
                # inequalities also need to go into $where clause
                self._check_size(op, c.value)
                loc = MongoClause.LOC_WHERE
                szop = ConstraintOperator(op.size_op)
                if self._rev:
                    szop.reverse()
                js_op = self._js_op_str(szop)
                expr = 'this.{}.length {} {}'.format(c.field.name, js_op, c.value)
        elif op.is_type():
            loc = MongoClause.LOC_WHERE
            type_name = self.JS_TYPES.get(c.value, None)
            if type_name is None:
                raise RuntimeError('Could not get JS type for {}'.format(c.value))
            typeop = '!=' if self._rev else '=='
            expr = 'typeof this.{} {} "{}"'.format(c.field.name, typeop, type_name)
        elif op.is_regex():
            expr = {c.field.name: {mop: c.value.pattern}}
        else:
            if mop is None:
                expr = {c.field.name: c.value}
            elif isinstance(c.value, bool):
                # can simplify boolean {a: {'$ne': True/False}} to {a: False/True}
                not_c_val = not c.value if self._rev else c.value
                expr = {c.field.name: not_c_val}
            else:
                expr = {c.field.name: {mop: c.value}}
        return loc, expr

    def _check_size(self, op, value):
        if not isinstance(value, int):
            raise ValueError('wrong type for size: {}'.format(value))
        if value < 0:
            raise ValueError('negative value for size: {}'.format(value))
        if op.is_size_lt() and value == 0:
            raise ValueError('value 0 is not allowed for size operator "{}"'.format(op))

    def _reverse_operator(self, op):
        """Reverse the operation e.g. since the conditions
        you provide are assertions of how things should be,
        e.g. asserting (a > b) leads to a search for (a <= b)

        :param op: Operator for any field/value
        :type op: ConstraintOperator
        """
        op = copy.copy(op)
        op.reverse()
        # check that we can map it
        if not str(op) in self.MONGO_OPS:
            raise ValueError('unknown operator: {}'.format(op))
        return op

    def _mongo_op_str(self, op):
        """Get the MongoDB string for an operator
        """
        return self.MONGO_OPS[str(op)]

    def _js_op_str(self, op):
        """Get JavaScript inequality operator equivalent
        """
        return self.JS_OPS.get(str(op), op)

    @property
    def is_reversed(self):
        return self._rev

class MongoQuery(object):
    """MongoDB query composed of MongoClause objects.
    """

    def __init__(self):
        """Create empty query.
        """
        self._main, self._where = [], []
        self._main2 = []

    def add_clause(self, clause):
        """Add a new clause to the existing query.

        :param clause: The clause to add
        :type clause: MongoClause
        :return: None
        """
        if clause.query_loc == MongoClause.LOC_MAIN:
            self._main.append(clause)
        elif clause.query_loc == MongoClause.LOC_MAIN2:
            self._main2.append(clause)
        elif clause.query_loc == MongoClause.LOC_WHERE:
            self._where.append(clause)
        else:
            raise RuntimeError('bad clause location: {}'.format(clause.query_loc))

    def to_mongo(self, disjunction=True):
        """Create from current state a valid MongoDB query expression.

        :return: MongoDB query expression
        :rtype: dict
        """
        q = {}
        # add all the main clauses to `q`
        clauses = [e.expr for e in self._main]
        if clauses:
            if disjunction:
                if len(clauses) + len(self._where) > 1:
                    q['$or'] = clauses
                else:
                    # simplify 'or' of one thing
                    q.update(clauses[0])
            else:
                for c in clauses:
                    q.update(c)
        # add all the main2 clauses; these are not or'ed
        for c in (e.expr for e in self._main2):
            # add to existing stuff for the field
            for field in c:
                if field in q:
                    q[field].update(c[field])
                else:
                    q.update(c)
        # add where clauses, if any, to `q`
        if self._where:
            wsep = ' || ' if self._where[0].is_reversed else ' && '
            where_clause = wsep.join([w.expr for w in self._where])
            if disjunction:
                if not '$or' in q:
                    q['$or'] = []
                q['$or'].append({'$where': where_clause})
            else:
                q['$where'] = where_clause
        return q

    @property
    def where_clauses(self):
        return self._where

    @property
    def clauses(self):
        return self._main

    @property
    def all_clauses(self):
        return self._main + self._where


def main():
    """Run an interactive CLI program that
    prints the output of running query() on the input string.
    """
    import sys, signal

    def _exit():
        print("Thank you for playing Simple Mongo Query!")
        sys.exit(0)

    signal.signal(signal.SIGINT, lambda s, f: sys.stdout.write("\n") or _exit())

    while 1:
        expr = input("Enter query: ").strip()
        if not expr:
            break
        try:
            q = to_mongo(expr)
        except BadExpression as e:
            print(("Error! Cannot parse '{}'".format(e.expr)))
            continue
        print(("Result: {}".format(q)))
    _exit()

if __name__ == '__main__':
    main()

