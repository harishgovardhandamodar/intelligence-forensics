"""Embedding-reconstruction simulation engine (server side, P8).

Demonstrates how repeated similar queries leak sensitive values when a
gateway stores query/response embeddings: masked variants of one secret
(`***-**-6789`, `123-**-****`) cluster by cosine similarity, and
position-wise assembly of the unmasked characters recovers the full value.

All secrets here are synthetic and seeded — values are drawn from reserved
documentation ranges (EXAMPLE key shapes, 900-series SSNs, 4242 test PANs)
and can never collide with real credentials by construction.
"""
