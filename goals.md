The Formbar will be split into two parts. The Formbar application, and bot modules.
The Formbar Application will be bare-bones. It will track individual students, group them into classes, and track “lessons”. These can be tracked by three database tables.
It will also have a webserver and websocket server
Will use flask-socketio
https://flask-socketio.readthedocs.io/en/latest/
For now, sockets will be used primarily as real-time api calls, especially for things like bots. Chat will be a secondary feature to come later. Prepare “rooms” using socketio now, but do not work on the chat feature yet.
The webserver will look and act like it does now. Keep the layout of existing templates, but the CSS needs combined into a cohesive stylesheet. You may edit the colors and superficial features like font types, but the layout must remain generally the same.
All endpoints that return a template or HTML must also check for a query parameter called “return”. If it is equal to “json” AND the user has sufficient API permissions, the endpoint will return the relevant information in a JSON object instead of HTML. This JSON api is to be used to make and “Advanced/Expert Mode” panel.
Core features must include: TUTD, HELP/POTTY buttons
Anytime a change is made on the Formbar, it will send out a websocket signal to all users that have sufficient permission to access the data related to the change (for example: students won’t be sent signals about someone sending in a help ticket, but teachers will).
All neopixels and pygame functions will be handled by a separate bot module. The bot module will log in as a bot user and connect to the websocket server. All lights for TUTD and other features will be calculated and displayed by the bot. Sound effects and background music will also be handled through pygame by the bot. The lights and sounds are handled whenever it receives a websocket state change message.

