# Dustkid TV

Plays recent Dustforce replays from dustkid.com


## Dependencies

 [Python 3](https://www.python.org/downloads/) and the following libraries are needed to run this program:

```
pillow
numpy
pandas
dustmaker
certifi
emoji
```

Install them with `pip install -r requirements.txt` any other preferred method (note that [Dustmaker](https://github.com/msg555/dustmaker) needs to be version >= 1.1.1).


## Usage

This assumes that you are using [Dustmod](https://dustmod.com/).

First, set file associations in Dustmod (Dustmod → About → Set file associations).

Find your Dustforce game folder. If you are using the Steam version, it will look something like `C:/Program Files (x86)/Steam/steamapps/common/Dustforce/`. Edit the `config.json` file in this program's main folder so that it points to your Dustforce game folder and your Dustmod executable:

```
{
  "dustmod":    "C:/Program Files (x86)/Steam/steamapps/common/Dustforce/dustmod.exe",
  "path":       "C:/Program Files (x86)/Steam/steamapps/common/Dustforce/"
  "local_path": "C:/Program Files (x86)/Steam/steamapps/common/Dustforce/"
}
```

If you are using the DRM-free Windows version of Dustforce, local_path should point to the Dustforce folder in AppData, usually located in `C:\Users\USERNAME\AppData\Roaming\Dustforce`.

Alternatively, you can set the `DFPATH`, `DFDAILYPATH` and `DFEXE` environmental variables.

Run `main.py` to launch Dustkid TV.


## Self-contained executable

Optionally, `build.py` uses `pyinstaller` to create a standalone executable, which can be used on systems where Python and the libraries listed above are not available.

To use the standalone executable, put the path to your Dustforce game folder and Dustmod executable in `config.json` as explained above, and run `main.exe`.


## Notes

Dustkid Daily replays will be played incorrectly if you have not downloaded/played today's daily. Access Dustkid Daily in the Dustmod Community Nexus to fix them.

This program caches custom map files and replay files. It is safe to delete the contents of the `dfreplays` and `dflevels` folders.


## Thanks

Thanks to Msg and Joel for sharing ideas / dustbot code.  
Thanks to jdude, Skyhawk and loginn for help with this project.  
Wallpaper by @tashizuna
