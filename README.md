# RunningVolume_Injury

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

Project predicting injury rates in runners based on information about training volume


## Project scope

When people get into running at various levels, they will typically encounter several pieces of advice for staying injury free, the main one being load management. One of the golden rules for load management is to ‘increase volume by 10% each week to avoid injury’ this is generally taken as gospel. 
Currently recovering from my own injury, my perspective as a data scientist has led me to ask ‘what do the data say?’ What is the baseline injury rate for runners maintaining volume/intensity, and what is the relative injury rate for various increases in volume? Some research has been done on this but it is far from conclusive. I hope to help users understand if their recent training puts them at a higher risk of injury.

Using machine learning, and a dataset detailing training and injuries for a group of competitive medium to long distance runners, I’ll attempt to create a model that predicts relative risk of injury over time for various training details like volume and intensity. Then, I will extract user training data recorded with wearables via API, and show a user their relative risk of injury over time based on predictions made by the model.


## References
Paper that makes original predictions on the dataset
https://pure.rug.nl/ws/portalfiles/portal/183763727/_15550273_International_Journal_of_Sports_Physiology_and_Performance_Injury_Prediction_in_Competitive_Runners_With_Machine_Learning.pdf

Python API wrapper for Garmin Connect adapted from https://github.com/cyberjunky/python-garminconnect

## Project Organization

```
├── LICENSE            <- Open-source license if one is chosen
├── Makefile           <- Makefile with convenience commands like `make data` or `make train`
├── README.md          <- The top-level README for developers using this project.
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── docs               <- A default mkdocs project; see www.mkdocs.org for details
│
├── models             <- Trained and serialized models, model predictions, or model summaries
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── pyproject.toml     <- Project configuration file with package metadata for 
│                         Runningprojectmodule and configuration for tools like black
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
├── setup.cfg          <- Configuration file for flake8
│
└── Runningprojectmodule   <- Source code for use in this project.
    │
    ├── __init__.py             <- Makes Runningprojectmodule a Python module
    │
    ├── config.py               <- Store useful variables and configuration
    │
    ├── dataset.py              <- Scripts to download or generate data
    │
    ├── features.py             <- Code to create features for modeling
    │
    ├── modeling                
    │   ├── __init__.py 
    │   ├── predict.py          <- Code to run model inference with trained models          
    │   └── train.py            <- Code to train models
    │
    └── plots.py                <- Code to create visualizations
```

--------
