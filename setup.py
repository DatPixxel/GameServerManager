"""
Setup-Datei für Game Server Manager Pro
"""

from setuptools import setup, find_packages

setup(
    name="gameservermanager",
    version="3.31",
    packages=find_packages(),
    install_requires=[
        'customtkinter>=5.2.0',
        'flask>=2.3.0',
        'requests>=2.31.0',
        'psutil>=5.9.0',
        'pillow>=10.0.0',
        'argon2-cffi>=21.3.0',
        'bcrypt>=4.0.0',
    ],
    python_requires='>=3.8',
)
