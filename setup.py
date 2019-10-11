import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="LeMDT",
    version="0.0.1",
    author="Antonio Ortega",
    author_email="antonio.ortega@kuleuven.vib.be",
    description="Track and interact with flies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/flysleeplab/learning-memory-feedback-and-tracking",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: Ubuntu 18.04",
    ],
    include_package_data=True,
    install_requires = ['imutils', 'Pillow', 'psutil', 'pyfirmata', 'opencv-python', 'coloredlogs','numpy', 'pandas', 'sklearn', 'pyyaml', 'ipdb'],
    dependency_links=[
        'https://github.com/basler/pypylon/releases/download/1.4.0/pypylon-1.4.0-cp37-cp37m-linux_x86_64.whl'],
    python_requires='>=3.7.0',
)
