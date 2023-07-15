# Curly Brackets

## It's finally here, and about time too

This repository contains nearly all the event-organizing tools I built out over the years. This includes: 
- The player pool assignment scheduling optimizer
- The bracket pdf generator
- Some API methods for interfacing with the [start.gg GraphQL API](https://developer.start.gg/explorer) and the [Challonge v1 API](https://api.challonge.com/v1), although the latter is rather dated

Everything is written in Python, and designed to work with Python 3.8. It can even be installed as a module if you want!

Right now my code is still very messy and inconsistent in several places. I'm not really sure how useful most of this is for others even once it gets to a more usable state. That said, I'm glad to finally move this over to a public repository so that any people interested in contributing could get the opportunity.

Some of the future development hopes and plans for this repository are: 
- Automatically advance players with first-round byes when generating pdfs
- Refactor the `assignment` submodule to be more object-oriented
- Better integrate multithreading and multiprocessing capabilities
- Create functionality for the Challonge v2 API
- Review the `assignment` submodule for inefficiencies and potential improvements
- _Actually add comments and docstrings to stuff_
- Add user-friendly macro functions to create pdf brackets directly from start.gg and Challonge bracket links

Feel free to fork and make contributions to this repository. I'm still mostly self-taught as far as "proper" developer goes, so please bear with me as I make changes. Thanks for reading!

## License
[BSD 3](LICENSE)