from DDV import VERSION
from setuptools import setup, find_packages

setup(
    name='DDV',
    version=VERSION,
    description='Visualization tool for fasta files.  Supports whole genome alignment and multiple sequence alignment.',
    author='Josiah Seaman, Bryan Hurst',
    author_email='josiah.seaman@gmail.com',
    license='BSD',
    packages=find_packages(exclude=('build', 'obj', 'www-data')),
    include_package_data=True,
    install_requires=[
        'Pillow>=3.2.0',
        'six>=1.10.0',
        'psutil>=4.3.1',
        'blist>=1.3.6',
        'numpy>=1.13.3',
        'natsort>=5.1.1',
    ],
    url='https://github.com/josiahseaman/DDV',
    download_url='https://github.com/josiahseaman/DDV',  # TODO: post a tarball
    keywords=['bioinformatics', 'dna', 'fasta', 'chain', 'alignment'],
    classifiers=[
        'Development Status :: 4 - Beta',  # 5 - Production/Stable
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)