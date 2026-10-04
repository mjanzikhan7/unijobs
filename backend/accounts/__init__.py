"""Who is using the system, and what they are allowed to do.

Innermost alongside :mod:`institutions`: it knows about users and roles, and nothing about jobs,
crawling or screening. The owner foreign keys elsewhere point at ``settings.AUTH_USER_MODEL``
rather than at this app, so no other app has to depend on it.
"""
