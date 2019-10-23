====================================
Welcome to Mephisto's documentation!
====================================

**Mephisto** aims to deliver a smoother and more intuitive workflow for making plots
with the python extension of the `ROOT <https://root.cern.ch/>`_ Data Analysis
Framework. By enhancing the functionality of the fundamental classes implemented in
**ROOT** and offering simple and efficient I/O solutions for frequent tasks the user can
hopefully dedicate more time to *make pretty histograms*!

.. image:: https://img.shields.io/badge/Mephisto-github-blue.svg?style=plastic&logo=github
    :align: center
    :target: https://github.com/fkrieter/mephisto

------------

-----------------
Design philosophy
-----------------

**Mephisto** contains **core classes** that offer the same basic functionality
as their **ROOT** pendants from which they inherit. In addition both new methods are
added and some existing ones are enhanced.

Example
-------

Let's consider an example: The **Histo1D** class for example inherits from **ROOT**'s
`TH1D <https://root.cern.ch/doc/master/classTH1.html>`_ class. The ``Fill()`` method is
now extended to also allow filling the histogram with events from a **TTree** in a given
**TFile**. If you want to save the histogram as a PDF file for example, you can just use
the ``Print()`` method to do so. It even lets you change any **property** of the object
by simply adding it as a keyword argument.

All together it would look something like this:

.. code-block:: python

    h = Histo1D("name", "title", 100, 0.0 100.0)

    h.Fill("path/to/file.root",
        tree="treename",
        varexp="tau1Pt",
        cuts=["MET>150", "jet1Btag==1"],
        weight="evt_weight")

    h.Print("tau1Pt.pdf", linewidth=5)

Wait, what's a property?
------------------------

Basically anything you can access and change with getter and setter method of the form
``Get<PropertyName>()`` and ``Set<PropertyName>()``. In the light of above's example
then *`linewidth'* would be a property of a **Histo1D** object, since it has the methods
``GetLineWidth()`` and ``SetLineWidth()`` (as it inherits from **TH1D**). So make sure
to check out the official **ROOT** `documentation
<https://root.cern.ch/doc/master/index.html>`_ to find out which properties are
available for any of the **core classes** parents!

Quick start guide
-----------------

Want to learn how to use **Mephisto**? Take the interactive **Jupyter** tutorial
`here <https://github.com/fkrieter/mephisto/tree/master/tutorial>`_ and follow the
instructions. This will get you up too speed in no time!

------------

=======
Content
=======

In the following an overview of all available modules and classes is listed.

-------------
Core classes:
-------------

.. toctree::
    :maxdepth: 2

    mephisto.Histo1D
    mephisto.Histo2D
    mephisto.Stack
    mephisto.Graph
    mephisto.Canvas
    mephisto.Legend
    mephisto.Line
    mephisto.Pad
    mephisto.Text
    mephisto.Arrow

--------------------------
Other classes and modules:
--------------------------

.. toctree::
    :maxdepth: 2

    mephisto.IOManager
    mephisto.Plot
    mephisto.RatioPlot
    mephisto.ContributionPlot
    mephisto.SensitivityScan
