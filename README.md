# WoT-PL Integration with Large Language Models (LLMs)

## Overview
This repository contains the implementation code for the experiments described in the paper "WoT-PL - Harnessing Large Language Models for IoT Schema Translation: A Conceptual Framework and Preliminary Findings". 
The paper discusses using LLMs to automate the translation of IoT device data into standardized Web of Things (WoT) Thing Descriptions. 
This repository includes the necessary scripts to replicate the experiments, measure the performance, and evaluate the accuracy and reliability of the generated WoT descriptions.

## Connection between Paper and Code
The codebase is structured to support the experiments outlined in the paper directly. It includes modules for:
- Fetching and processing data from IoT devices using the `ioBroker` system.
- Utilizing LLMs such as OpenAI's GPT and Anthropic's Claude models to translate device properties into WoT format.
- Validating the generated descriptions against the WoT standard.
- Generating performance and accuracy reports as discussed in the paper's findings.

## Installation
To run the scripts, you need Python 3.8 or later. First, clone this repository and then install the required Python packages:

```bash
git clone <this-repository>
cd <repository-folder>
pip install -r requirements.txt
```

## How to Run
The experiment process is divided into two main scripts:

1. **main.py** - This script is responsible for initiating the translation process using LLMs. It fetches IoT device data, processes it, and sends it to the LLMs to generate WoT descriptions.

2. **control.py** - After running `main.py`, execute this script. It evaluates the generated WoT descriptions against validation metrics and generates reports on the performance and accuracy of the LLM outputs.

### Running the Scripts
To start the experiments, run the following commands in sequence:

```bash
python main.py  # Starts the data fetching and translation process
python control.py  # Runs the metrics and generates reports
```

## Reports
After running the above scripts, the results will be available in the specified output directories within the repository. These include JSON files with the raw outputs from the LLMs and PNG images containing performance and accuracy graphs.

## License
This project is licensed under the MIT License - see the LICENSE file for details.
