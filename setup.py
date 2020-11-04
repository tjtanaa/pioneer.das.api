import setuptools

setuptools.setup(
    name="pioneer_das_api", # Replace with your own username
    version="0.3.0",
    author="Leddartech",
    description="Pioneer's das api",
    packages=[
        'pioneer', 
        'pioneer.das', 
        'pioneer.das.api', 
        'pioneer.das.tests',
        'pioneer.das.api.samples', 
        'pioneer.das.api.sensors', 
        'pioneer.das.api.sources',
        'pioneer.das.api.datasources',
        'pioneer.das.api.datasources.virtual_datasources'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    dependency_links=["https://pioneer:yK6RUkhUCNHg3e1yxGT4@svleddar-gitlab.leddartech.local/api/v4/projects/481/packages/pypi/simple/pioneer-common"],
    install_requires=[
        'numpy',
        'opencv-python',
        'open3d',
        'transforms3d',
        'pioneer-common>=0.3',
        'six',
        'ruamel.std.zipfile',
        'pandas',
        'tqdm',
        'sklearn',
        'utm',
        'pyyaml'
    ],
    include_package_data=True
)