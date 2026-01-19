"""
FreeRADIUS Integration Module

This module provides dual integration with FreeRADIUS:
1. rlm_python - Direct Python module for FreeRADIUS
2. REST API endpoint - /api/radius-auth for rlm_rest

Both methods use the same RadiusBackendManager for authentication.
"""

__all__ = ['freeradius_module']
