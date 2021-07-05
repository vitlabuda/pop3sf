# POP3SF – POP3 Server Framework
**POP3SF** (POP3 Server Framework) is a free & open-source POP3 framework written in Python 3 that allows the built-in POP3 server to fetch email messages from a variety of data sources and provide them to clients via the POP3 protocol.

The server gets emails from Python classes called **adapters**. See the [Adapers](#adapters) section for details.



## Features and characteristics
The main purpose of this program is not to act as a conventional POP3 server that provides access to a mailbox which contains messages received via SMTP.
In particular, it has been designed to allow a server admin to fetch messages from their own (non-standard) source, so they can read them using an ordinary email client, not needing to code an app (for multiple platforms) for this purpose, which can be especially useful on platforms where self-made apps cannot be normally installed, like iOS. 
For example, with the right adapter, one can connect this framework to a database containing logs from a script and read them using an ordinary email client.

The main features of the built-in POP3 server include:
* SSL/TLS support
* UTF-8 transfer support *(not supported by a lot of other POP3 servers)*
* support for multiple concurrent client connections
* the ability to listen on multiple IP addresses/ports at once
* very rudimentary invalid password tries limiter and delayer
* special non-standard [read-only mailbox access mode](READONLY-CAPABILITY)



## RFC standards compliance
The built-in POP3 server complies with the following RFC standards:
* **RFC 1939** – Post Office Protocol – Version 3 (STD 53) ([HTML](https://datatracker.ietf.org/doc/html/rfc1939))
* **RFC 2449** – POP3 Extension Mechanism ([HTML](https://datatracker.ietf.org/doc/html/rfc2449))
* **RFC 3206** – The SYS and AUTH POP Response Codes ([HTML](https://datatracker.ietf.org/doc/html/rfc3206))
* **RFC 6856** – Post Office Protocol Version 3 (POP3) Support for UTF-8 ([HTML](https://datatracker.ietf.org/doc/html/rfc6856))



## Adapters
The "bridges" between data sources and the built-in POP3 server are called **adapters**. 
An adapter is a Python class that extends the [AdapterBase](src/pop3sf/adapters/AdapterBase.py) class and implements its abstract methods.
The adapters are located in the [src/pop3sf/adapters](src/pop3sf/adapters) directory.

The adapter the server is using can be set in the [Settings.py](src/pop3sf/Settings.py) file.



### Included adapters
Five adapters are included with the program:
* [ListAdapter](src/pop3sf/adapters/ListAdapter.py) – provides emails from a Python ``list`` object *(not much practical use – for testing purposes)*
* [DirectorySingleuserAdapter](src/pop3sf/adapters/DirectorySingleuserAdapter.py) – provides emails from a filesystem directory
* [DirectoryMultiuserAdapter](src/pop3sf/adapters/DirectoryMultiuserAdapter.py) – provides emails from a filesystem directory, supporting multiple user accounts
* [MySQLSingleuserAdapter](src/pop3sf/adapters/MySQLSingleuserAdapter.py) – provides emails from a MySQL table
* [MySQLMultiuserAdapter](src/pop3sf/adapters/MySQLMultiuserAdapter.py) – provides emails from a MySQL table, supporting multiple user accounts

See these adapter classes' docstrings for usage information. 

Related to these directory and MySQL adapters are the included auxiliary libraries, located in the [auxiliary_libs](auxiliary_libs) directory. 
These helper libraries make it easy to add messages to the data sources used by these adapters from other Python programs.
In addition, if the data source supports multiple user accounts, these libraries can manage them.



### Programming your own adapter
When programming your own adapter, extend the [AdapterBase](src/pop3sf/adapters/AdapterBase.py) class, implement its abstract methods and **follow all the docstrings**. 
Then, don't forget to put the adapter to the ``get_adapter()`` method of the [Settings.py](src/pop3sf/Settings.py) file.



## Setting up & running the server

### 1. Requirements
   * **Linux**
   * **Python 3.7+**
   
   The program was tested on Python 3.7 (Debian 10), Python 3.8 (Ubuntu 20.04) and Python 3.9 (Debian 11).

### 2. Install the dependencies
   The server requires the ``pip`` and ``venv`` Python 3 packages to be installed.
   
   On Debian/Ubuntu and their derivatives, execute the following:
   ```
   sudo apt update 
   sudo apt install python3 python3-pip python3-venv
   ```


### 3. Change the server configuration to fit your needs
   The server configuration, including the used adapter, can be altered in the **[Settings.py](src/pop3sf/Settings.py)** file. 
   Follow the docstrings and code comments there.


### 4. Run the server
   The bash script [run_pop3sf.sh](src/run_pop3sf.sh) creates a virtual environment and downloads the necessary Python libraries if needed, and then runs the program:

   ```
   ./run_pop3sf.sh
   ```


### 5. Install the systemd service
   To run the server automatically on startup, a systemd service should be created (on Linux distributions that use systemd).

   A systemd service file, [pop3sf.service](src/pop3sf.service), is already included with the program: 

   ```
   sudo nano pop3sf.service  # Edit the service file so it matches your server's environment
   sudo cp pop3sf.service /lib/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable pop3sf
   sudo systemctl start pop3sf
   ```


## Licensing
This project is licensed under the 3-clause BSD license. See the [LICENSE](LICENSE) file for details.

Written by [Vít Labuda](https://vitlabuda.cz/).
