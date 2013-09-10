Querying with smoqe
====================

The :py:func:`smoqe.to_mongo` function converts a smoqe query string or list into a MongoDB dict.

If you are using ``pymongo`` to interface with MongoDB, then you can use the drop-in
replacement :py:class:`smoqe.MongoClient`.

Extending smoqe
---------------

The whole point of ``smoqe`` is to be a *simple* query language.
Only part of the full MongoDB syntax is supported. However, keep in mind
that :py:func:`smoqe.to_mongo` outputs a dictionary, which can be extended
further, so you can use smoqe to simplify just the simple parts of queries.
For example, to join two simple experessions with ``$nor`` ::

    import smoqe
    q = {'$nor':[smoqe.to_mongo('a > 10'), smoqe.to_mongo('b < 12')]}

All the syntax details of the query language are given in :py:func:`smoqe.to_mongo`.

Performance
-----------

Since ``smoqe`` simply translates queries to MongoDB syntax, unless you have a
*ridiculously* large query (thousands of expressions)
the performance of the query will be practically identical to its MongoDB equivalent.

API Documentation
-----------------

.. currentmodule:: smoqe

.. autofunction:: to_mongo

.. autoclass:: MongoClient
