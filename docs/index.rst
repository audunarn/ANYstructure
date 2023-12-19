.. image:: _static/ANYstructure_logo.jpg
  :width: 400
  :alt: ANYstructure logo

Welcome to ANYstructure's documentation!
========================================
This page mainly document the API.

For GUI documentation, see the following link:

`ANYstructure GUI documentation <https://sites.google.com/view/anystructure/documentation>`_

Python
------
To install ANYstructure use PIP:

.. code:: shell

   pip install anystructure

API basic usage:

.. code:: shell

   from anystruct import api
   FlatStruct = api.Flatstru(*INPUT CALCULATION DOMAIN*)
   CylStru = api.CylStru(*INPUT CALCULATION DOMAIN*)

The GUI can be started by:

.. code:: shell

   from anystruct import gui
   gui.main()

Windows executable
------------------
The latets release of ANYstructure can be downloaded here:

`Github releases <https://github.com/audunarn/ANYstructure/releases>`_

Install and launch the app.

.. toctree::
    :hidden:

   install
   support
   api