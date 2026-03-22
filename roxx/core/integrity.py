# -*- coding: utf-8 -*-
# RoXX - Robust & Scalable Authentication Proxy
# Copyright (C) 2026 Thomas Sautier (tsautier@users.noreply.github.com)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

import hashlib
import os
from pathlib import Path
from typing import Dict, List

class IntegrityManager:
    """
    Manages the cryptographic integrity of the RoXX codebase.
    Used to prove authorship and detect unauthorized modifications.
    """
    
    CORE_DIRS = ["roxx/core", "roxx/web", "roxx/utils"]
    
    @classmethod
    def generate_manifest(cls, base_dir: str = ".") -> Dict[str, str]:
        """Generates SHA-256 hashes for all files in core directories"""
        manifest = {}
        base_path = Path(base_dir)
        
        for d in cls.CORE_DIRS:
            dir_path = base_path / d
            if not dir_path.exists(): continue
            
            for file_path in dir_path.rglob("*.py"):
                if "__pycache__" in str(file_path): continue
                
                with open(file_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    relative_path = str(file_path.relative_to(base_path))
                    manifest[relative_path] = file_hash
                    
        return manifest

    @classmethod
    def verify_integrity(cls, expected_manifest: Dict[str, str], base_dir: str = ".") -> List[Dict]:
        """Verifies current files against an expected manifest"""
        results = []
        current_manifest = cls.generate_manifest(base_dir)
        
        for path, expected_hash in expected_manifest.items():
            current_hash = current_manifest.get(path)
            if not current_hash:
                results.append({"path": path, "status": "MISSING"})
            elif current_hash != expected_hash:
                results.append({"path": path, "status": "MODIFIED"})
            else:
                results.append({"path": path, "status": "OK"})
                
        return results
