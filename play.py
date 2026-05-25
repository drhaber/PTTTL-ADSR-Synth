"""
THIS FILE IS 100% AI GENERATED, NOT A SINGLE LINE WAS WRITTEN BY A HUMAN, PROCEED WITH CAUTION.
"""

import sys
import subprocess
import os
import logging

import ptttlwadsr_parser as parser
from audio import ptttl_to_wav as render_ptttl_to_wav, get_ptttl_output_path

# Set up logging for CLI usage
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
_LOGGER = logging.getLogger(__name__)

def main():
    if len(sys.argv) < 2:
        print('Usage: play "<ptttl_string>"')
        sys.exit(1)

    ptttl_string = " ".join(sys.argv[1:]).strip()
    output_wav_path = get_ptttl_output_path(ptttl_string)

    try:
        _LOGGER.info("🔍 Parsing string...")
        ptttl_parser_instance = parser.PTTTLParser()
        ptttl_data = ptttl_parser_instance.parse(ptttl_string)

        _LOGGER.info("🎛️ Rendering audio ...")
        # Updated to reference ptttl_data.wadsr instead of .instruments
        _LOGGER.info("🎼 Tracks=%d, patches=%s", len(ptttl_data.tracks), ptttl_data.wadsr)
        
        render_ptttl_to_wav(ptttl_string, output_wav_path)

        _LOGGER.info("📁 Exported audio file to %s", output_wav_path)

        # Play it through your sound card immediately
        player = None
        if subprocess.run(["which", "mpv"], capture_output=True).returncode == 0:
            player = ["mpv", "--no-video"]
        elif subprocess.run(["which", "aplay"], capture_output=True).returncode == 0:
            player = ["aplay"]
        
        if player:
            subprocess.run(player + [output_wav_path])
        else:
            _LOGGER.warning("❌ Audio file saved to %s, but no CLI media player was found.", output_wav_path)

    except Exception as e:
        _LOGGER.error("❌ Error during playback: %s", e)
        sys.exit(1)

if __name__ == "__main__":
    main()