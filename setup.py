from setuptools import setup, find_packages

setup(
    name="reducetoken",
    version="1.0.0",
    description="Code Knowledge Graph and Token Saver for AI Agents (Antigravity, Copilot, Cursor, OpenCode, Claude)",
    author="TuilaTammmmm",
    url="https://github.com/TuilaTammmmm/ReduceToken",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "reducetoken=reducetoken.cli:main",
            "rt=reducetoken.cli:main",
            "rtk=reducetoken.cli:main",
            "rd=reducetoken.cli:main",
        ],
    },
    python_requires=">=3.8",
)
