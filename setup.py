from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="arbot",
    version="1.0.0",
    author="Euiyun Kim",
    author_email="geniuskey@gmail.com",
    description="A modular, real-time arbitrage trading bot for cryptocurrency exchanges",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FinAI6/arbot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "analytics": [
            "pandas-ta>=0.3.14b",
            "scikit-learn>=1.3.0",
            "matplotlib>=3.7.0",
            "seaborn>=0.12.0",
        ],
        "monitoring": [
            "prometheus-client>=0.17.0",
            "grafana-client>=3.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "arbot=main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)