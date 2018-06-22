import os
import sys
import subprocess

my_path = os.path.abspath(os.path.dirname(__file__))
my_path = '\\'.join(my_path.split('\\')[:-2])
print(my_path)
os.chdir(my_path)