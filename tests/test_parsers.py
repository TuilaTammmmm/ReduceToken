import unittest
from reducetoken.parsers.python_parser import parse_python_file
from reducetoken.parsers.js_ts_parser import parse_js_ts_file
from reducetoken.parsers.generic_parser import parse_generic_file


class TestParsers(unittest.TestCase):
    def test_python_parser(self):
        code = '''
"""Auth module for user verification."""
import os
from datetime import datetime, timedelta
from .models import User

class AuthManager:
    """Manages authentication tokens."""
    def __init__(self, secret: str):
        self.secret = secret

    def verify_token(self, token: str) -> bool:
        return True

def generate_jwt(user_id: int) -> str:
    now = datetime.now()
    return "sample_token"
'''
        res = parse_python_file("auth.py", code)
        self.assertEqual(res.language, "python")
        self.assertEqual(res.summary, "Auth module for user verification.")
        
        # Check symbols
        names = [s.name for s in res.symbols]
        self.assertIn("AuthManager", names)
        self.assertIn("generate_jwt", names)

        # Check imports
        sources = [i.source for i in res.imports]
        self.assertIn("os", sources)
        self.assertIn("datetime", sources)
        self.assertIn(".models", sources)

    def test_js_ts_parser(self):
        code = '''
import React, { useState, useEffect } from 'react';
import { fetchUserData } from './api/user';
import './styles.css';

export interface UserProfile {
    id: string;
    name: string;
}

export class UserService {
    static async getUser(id: string) {
        return fetchUserData(id);
    }
}

export function renderUserHeader(user: UserProfile) {
    return `Hello ${user.name}`;
}

export const logout = () => {
    localStorage.clear();
};
'''
        res = parse_js_ts_file("user.tsx", code, language="typescript")
        names = [s.name for s in res.symbols]
        self.assertIn("UserProfile", names)
        self.assertIn("UserService", names)
        self.assertIn("renderUserHeader", names)
        self.assertIn("logout", names)

        sources = [i.source for i in res.imports]
        self.assertIn("react", sources)
        self.assertIn("./api/user", sources)

    def test_generic_parser(self):
        go_code = '''
package auth

import (
    "fmt"
    "net/http"
)

func ValidateSession(r *http.Request) bool {
    return true
}
'''
        res = parse_generic_file("auth.go", go_code, language="go")
        self.assertEqual(res.summary, "Go package: auth")
        sources = [i.source for i in res.imports]
        self.assertIn("fmt", sources)
        self.assertIn("net/http", sources)
        sym_names = [s.name for s in res.symbols]
        self.assertIn("ValidateSession", sym_names)


if __name__ == "__main__":
    unittest.main()
