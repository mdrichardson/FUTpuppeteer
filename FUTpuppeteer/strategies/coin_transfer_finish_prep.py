import os

my_path = os.path.abspath(os.path.dirname(__file__))
my_path = '\\'.join(my_path.split('\\')[:-2])
os.chdir(my_path)


def prep(gain_coins, lose_coins):
    directory = os.path.dirname(os.path.abspath(__file__)) + '\coin_transfer_finish.py'
    os.system("cmd.exe /c python {} {} {}".format(directory, gain_coins, lose_coins))


if __name__ == "__main__":
    prep(1, 5)