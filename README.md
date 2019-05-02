# PyDoctorSender - An unofficial Python API for DoctorSender

PyDoctorsSender is an unofficial API wrapper for the email sending system [DoctorSender](https://www.doctorsender.com/en). It provides and easy and accessible way to automate
everything you can do on the GUI and more.

The full documentation can be found here: [docs](https://htmlpreview.github.io/?https://github.com/R4h4/PyDoctorSender/blob/master/docs/build/html/index.html)

## Installation
```installation
pip install pydoctorsender
```

## Usage

Usage is simple, here is an example on how to get all sending lists in your account:
```get_lists
from doctorssender import DoctorSenderClient

client = DoctorSenderClient('user@doctorsender.com', 'example_api_token')
client.lists()
```

All calls return standard Python data types and objects. Example return:
```lists_return
{'example_list': {'test': '0',
  'count': '123456',
  'created_at': '2019-01-01 01:23:45',
  'ready': '1',
  'last_amount_update': '2019-04-25 00:00:00'},
 'test_list': {'test': '0',
  'count': '1000',
  'created_at': '2019-02-02 00:10:10',
  'ready': '1',
  'last_amount_update': '2019-04-25 02:30:40'}
```

## My2Cents
If you are already punished by having to use one of the oldest systems on the 
market, this package will make your life at least a little bit easier - At least until 
DoctorSender changes your API key, without previous warning, in production.