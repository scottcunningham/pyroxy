pyroxy
======

A simple, configurable Python HTTP proxy.

Features:
  - Keyword blocking: scans pages for a list of given keywords, and shows an error page if they occur.
      * Keywords for page blocking are kept in a config file ``bad_keywords.conf`` and are line-separated.
      * The error page is also configurable through the file ``resources/banned.html``.
  - Hostname blocking: blocks connections to a given hostname. Like keyword blocking, blocked hostnames are kept in
    ``banned_hosts.conf``, and the error HTML should be in ``resources/banned.html``.
  - Other configurable error pages: connection errors in ``resources/connect.html``.
  - Automatic caching.
  - Admin web UI to add/remove blocked keywords and hostnames.
    
pyroxy listens on port 8080 by default.
