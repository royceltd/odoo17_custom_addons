### Odoo bulk sms (Kenya)

This package provides an easy interface for sending SMS in your laravel application. Open a free account [Royce BulkSMS](https://roycebulksms.com/), under API menu click generate API. Copy the API key and paste it in your .env file

### For support and equiries
- contact us via whatsapp/call +254713727937
- email developer@roycetechnologies.co.ke

## Features

- Provide an easy interface for sending bulk sms
- Provides a database table for storing sent text.
- An interface for viewing sent text (outbox)
- Provide a callback URL you add to your bulksms account. This will ensure that you receive delivery status back to your application (_coming soon_)

## Installation

- Download this app and put it in your addons folder
- Go to  app and search for Bulk sms
- install the module

### Integration

- Open a free account at [Royce BulkSMS](https://roycebulksms.com/)
- Under Api > api keys. Generate an API key and copy it.
- Open Bulk sms app in your odoo app.
- Under Config>api keys , Create an api key and save
- Under config> sender id, create a sender id with value of RoyceLtd

### How to use

- Under bulksms> send sms send a test message

### How to use from other models
- Search send.text model and sendCustomText with mobile number,text message, sender id parameters

### Sample code when sending from other models

- self.env['send.text'].sendCustomText('0713727937','We have received your payment, receipt number RCP0022 ','RoyceLtd')
