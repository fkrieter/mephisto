import setuptools

setuptools.setup(
    name="mephisto",
    version=0.1,
    author="fkrieter",
    author_email="",
    description="MakE Pretty HISTOgrams",
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/fkrieter/mephisto",
    packages=setuptools.find_packages(),
    classifiers=[
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Software Development",
        "Topic :: Scientific/Engineering",
        "Topic :: Utilities",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: MacOS",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],
    scripts=[],
    install_requires=["numpy<=1.16.5a0", "root_numpy<=4.8.0a0", "scipy<=1.2.2a0"],
)
