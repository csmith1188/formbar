### [Minor] sfx_fix
- Fixes #10 (Dynamic SFX Finder w/ Error Catching)
- New function playSFX( <sound file name, no extension> ) now plays pygame sounds
- New function in sfx module updateFiles() rescans the sfx/ folder
- sfx dictionary changed to 'sound' and is built from updateFiles()

### [Patch] Feb 16th
- Fixed #9
- Fixed #3

### color_fix
- added hex2dec() in colors module to convert #XXXXXX or XXXXXX format into tuplet values
- changed /colors to use r,g,b or hex
- /say now uses hex values for fg and bg

- Made the surveyBar sort by similar color, which is the only thing I set out to do
- Added *clearBar()*
- changed *fillBar()* to *tutdBar()*
- replaced *fillBar()* with *fillBar(color, stop, start)*, the fill parts of the bar with a chosen color
- Changed all settings to dictionaries for faster reference
- Changed settings to search for arguments in the settings dictionary automatically
- Added "captions" setting so that bar modes can operate without overwriting the text panel
