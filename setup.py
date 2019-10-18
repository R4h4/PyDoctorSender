from distutils.core import setup
setup(
  name = 'pydoctorsender',
  packages = ['pydoctorsender'],
  version = '0.12',
  license='MIT',
  description = 'An unofficial API wrapper for DoctorSender',
  author = 'Karsten Eckhardt',
  author_email = 'karsten.eckhardt@gmail.com',
  url = 'https://github.com/r4h4/PyDoctorSender',
  download_url = 'https://github.com/r4h4/PyDoctorSender/archive/v0.12.tar.gz',
  keywords = ['doctorsender', 'email', 'marketing', 'api'],   # Keywords that define your package best
  install_requires=[            # I get to this in a second
          'requests'
      ],
  classifiers=[
    'Development Status :: 5 - Production/Stable',  # "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7'
  ],
)