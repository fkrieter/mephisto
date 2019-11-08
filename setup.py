import os
import setuptools

os.system("grep -v '^#' requirements.txt | xargs -L1 pip install --user")

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
    install_requires=["root_numpy", "scipy"],
)
