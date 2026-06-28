"""
Setup configuration for laraflask-core.
Install with: pip install laraflask-core
"""

from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="laraflask-core",
    version="1.3.0",
    author="Laraflask Contributors",
    description="Laravel-inspired framework core for Flask — elegant, expressive, modern.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Laraflask-Community/laraflask-core",
    packages=find_packages(exclude=["tests*"]),
    package_data={
        "laraflask": ["py.typed"],
    },
    python_requires=">=3.10",
    install_requires=[
        # Core
        "flask>=3.1.0",
        "python-dotenv>=1.1.0",
        "jinja2>=3.1.4",
        "werkzeug>=3.1.0",
        "click>=8.1.8",
        # ORM
        "sqlalchemy>=2.0.36",
    ],
    extras_require={
        # pip install laraflask-core[all]
        "all": [
            "alembic>=1.14.0",
            "PyMySQL>=1.1.1",
            "psycopg2-binary>=2.9.10",
            "pgvector>=0.3.6",
            "redis>=5.2.1",
            "bcrypt>=4.2.1",
            "pyjwt>=2.10.1",
            "cryptography>=44.0.0",
            "flask-session>=0.8.0",
            "celery>=5.4.0",
            "croniter>=5.0.1",
            "apscheduler>=3.11.0",
            "email-validator>=2.2.0",
            "flask-cors>=5.0.0",
            "flask-socketio>=5.5.1",
            "boto3>=1.35.0",
            "twilio>=9.4.0",
        ],
        "mysql":         ["PyMySQL>=1.1.1"],
        "postgresql":    ["psycopg2-binary>=2.9.10"],
        "vector":        ["pgvector>=0.3.6", "psycopg2-binary>=2.9.10"],
        "redis":         ["redis>=5.2.1", "hiredis>=3.0.0"],
        "auth":          ["bcrypt>=4.2.1", "pyjwt>=2.10.1", "cryptography>=44.0.0"],
        "queue":         ["celery>=5.4.0", "kombu>=5.4.2"],
        "storage":       ["boto3>=1.35.0", "botocore>=1.35.0"],
        "notifications": ["twilio>=9.4.0"],
        "websocket":     ["flask-socketio>=5.5.1", "python-socketio>=5.11.0", "eventlet>=0.38.0"],
        "testing":       ["pytest>=8.3.0", "pytest-flask>=1.3.0", "factory-boy>=3.3.1", "faker>=33.0.0"],
        "dev": [
            "pytest>=8.3.0",
            "pytest-flask>=1.3.0",
            "pytest-cov>=6.0.0",
            "factory-boy>=3.3.1",
            "faker>=33.0.0",
            "flask-debugtoolbar>=0.16.0",
            "watchdog>=6.0.0",
        ],
        "production": ["gunicorn>=23.0.0", "gevent>=24.11.0"],
    },
    entry_points={
        "console_scripts": [
            "laraflask=laraflask.console.artisan:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Framework :: Flask",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
        "Typing :: Typed",
    ],
    keywords="flask laravel framework orm routing auth cache queue events",
)
