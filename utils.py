import os
import Domoticz
import traceback

import subprocess
import time
from datetime import datetime

class Utils:
    def readFile(filePath, isBinary):
        html = ''
        try:
            if (isBinary):
                with open(filePath,  'r+b') as fp:
                    html = fp.read()
            else:
                with open(filePath,  'r' , encoding='utf-8') as fp:
                    html = fp.read()

            Domoticz.Log('Read file: {}'.format(filePath))

        except Exception as err:
            Domoticz.Log(traceback.format_exc())
            Domoticz.Error('Error to read file : {}'.format(filePath))

        return html

    def writeText(text, filePath):
        try:
            with open(filePath,  'w' , encoding='utf-8') as fp:
                fp.write(text)
            Domoticz.Log('File created: {}'.format(filePath))
        except Exception as err:
            Domoticz.Log(traceback.format_exc())
