from datetime import datetime

from flask import Flask, redirect, render_template, request

from . import game_round, game_storage, git
from .env import GITHUB_URL, PRODUCTION, SECRET_KEY
from .game import Direction

app = Flask(__name__)

app.config.update(
    TESTING=not PRODUCTION(),
    DEBUG=not PRODUCTION(),
    SECRET_KEY=SECRET_KEY(),
)


@app.route("/")
def setup():
    """Use when first deployed to get the file to update."""

    return click(1)


@app.route("/click/<int:direction>")
def click(direction: int):
    """Handle a click event on the game board."""

    # Create new game if no game is loaded
    game, loaded = game_storage.load_or_new()

    # Try to create new round to make sure there is an active round
    if not loaded:
        try:
            game_round.start()
        except Exception:
            game_round.end(0, datetime.now())
            game_round.start()

    starting_grid = [[item for item in row] for row in game.get_grid()]

    move_score, game_over = game.make_move(Direction(direction))

    if not game_over:
        # Save game
        game_storage.save(game.get_grid(), starting_grid)
        game_round.add_score(move_score)

    else:
        # End game
        game_storage.delete()
        game_round.end(game.get_biggest_block(), datetime.now())

        # Create new game
        game, _ = game_storage.load_or_new()
        game_round.start()

    highscore_info = game_round.get_high_score()
    current_score = game_round.get_current_score()

    if highscore_info is None:
        highscore_info = (0, None)
    else:
        highscore_info = (highscore_info[0], highscore_info[1].strftime("%d %b, %Y"))

    git.update(
        render_template(
            "combined_readme.md",
            current=current_score,
            highscore=highscore_info[0],
            end_date=highscore_info[1],
            grid=game.get_grid(),
            server_address=request.url_root,
        )
    )

    # Need to add a cache busting query parameter to force the page to
    # fetch the latest version of the readme. Only needed when not logged
    # in to GitHub. Weirdly, when logged in, GitHub always fetches the
    # latest version of the readme.
    return redirect(GITHUB_URL() + "?cacheBust=" + str(datetime.now().timestamp()))
