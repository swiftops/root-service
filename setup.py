from setuptools import setup, find_packages

setup(
    name='Bot Engine Filter Service',
    version='1.0.0',
    description='This service is used to autocomplete the searchbox and redirect to the respective microservices based on the input given by the user',
    author='Sakina Shaikh',
    author_email='sakina.shaikh@digite.com',
    url='http://swiftops.digite.com/rootservice/root',
    keywords=["Swagger", "Root Service"],
    install_requires=open('requirements.txt').read(),
    packages=find_packages(),
    include_package_data=True,
    license='',
    long_description=open('README.md').read()
	#test_suite='nose.collector',
    #tests_require=['nose']
)