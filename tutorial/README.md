# Practice Time!

Hey there! Are you searching for a quick start manual on how to use **Mephisto** so that you can finally *make pretty histograms*?
Look no further! This folder contains several interactive tutorials to get you familiar with the main features.
If you're already familiar with **ROOT** histograms such as ```TH1D```, ```TH2D``` or ```THStack```, you're in for a treat:
The core classes of Mephisto like ```Histo1D```, ```Histo2D``` or ```Stack``` all inherit from their respective ROOT counterparts so that you can use them just like you normally would.
However, new or enhanced class methods await you, that will make your life much easier!

### Take it to the cloud...

If your a [CERN](https://home.cern/) user you can take the tutorial online without installing anything on your machine:

<p align="center">
<a href="https://cern.ch/swanserver/cgi-bin/go?projurl=https://github.com/fkrieter/mephisto.git"><img alt="SWAN" src="http://swanserver.web.cern.ch/swanserver/images/badge_swan_white_150.png"></a>
</p>

Make sure **Mephisto** and it's dependencies are installed in your current [SWAN](https://swan.web.cern.ch/) session: Open a terminal by clicking the respective icon in the top bar and run

```
pip install --user -e .
```

in the root directory of this project.

### ...or run the Jupyter notebooks locally

After installing **Mephisto** on you machine, navigate to the *tutorial* folder and fire up the [**Jupyter**](https://jupyter.readthedocs.io/en/latest/install.html) notebooks:

```
cd tutorial/
jupyter notebook [--browser firefox]
```

This will open a new tab in your browser (usually [Firefox](https://www.mozilla.org/firefox/) works best), where you can run the notebooks.

### Contents

This folder contains lessons for the following features:

1. **IOManager:** Read ROOT files and fill your histograms - quick and easy!
2. **Histo1D:** Plot 1-dimensional histograms.
3. **Stack:** Plot a stack of several 1-dimensional histograms without writing a million lines of code.
4. **Histo2D:** One more dimension!
5. ...more soon!

Within a notebook you can run each cell of code by hitting ```Ctrl```+```Enter```, or ```Shift```+```Enter``` to also skip to the next one afterwards. For more info on how to use Jupyter notebooks click [here](https://www.datacamp.com/community/tutorials/tutorial-jupyter-notebook).
