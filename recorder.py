#!/usr/bin/env python3

import argparse, datetime, logging, math, os, os.path, random, re, sys

try:
    import winsound
except Exception as e:
    logging.warning("sound output only supported on Windows")

from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import Qt, QUrl, QObject, Property, Signal, Slot

import audio

class Recorder(QObject):
    """docstring for Recorder"""

    def __init__(self, save_dir, prompts_filename, ordered=False, new_only=False, prompts_count=100, prompt_len_soft_max=None):
        super(Recorder, self).__init__()
        if not os.path.isdir(save_dir): raise Exception("save_dir '%s' is not a directory" % save_dir)
        self.save_dir = save_dir
        if not os.path.isfile(prompts_filename): raise Exception("prompts_filename '%s' is not a file" % prompts_filename)
        self.prompts_filename = prompts_filename
        self.prompts_count = prompts_count
        self.prompt_len_soft_max = prompt_len_soft_max
        self.ordered = ordered
        self.audio = audio.Audio()
        self.new_only = new_only

    def list_recorded_ids(self, save_dir):
        recorded_ids = []
        recorder_file_path = os.path.join(save_dir, "recorder.tsv")
        if not os.path.isfile(recorder_file_path): 
            return recorded_ids
        with open(recorder_file_path, mode='r') as recorder_file:
            for line in recorder_file:
                line_splitted = line.split('\t')
                if len(line_splitted) >= 3:
                    recorded_ids.append(line_splitted[3])
        return recorded_ids

    @Slot(QObject)
    def init(self, scriptModel):
        logging.debug("init: %s", scriptModel)
        self.window.setProperty('saveDir', self.save_dir)
        self.scriptModel = scriptModel
        self.window.setProperty('promptsName', os.path.splitext(os.path.basename(self.prompts_filename))[0])
        for (script_id, script) in self.get_scripts_from_file(self.prompts_count, self.prompts_filename, self.ordered, split_len=self.prompt_len_soft_max, new_only=self.new_only):
            self.window.appendScript({'script': script, 'script_id': script_id, 'filename': ''})

    @Slot(bool)
    def toggleRecording(self, recording):
        logging.debug('toggleRecording: recording is now %s', recording)

    @Slot()
    def startRecording(self):
        size = self.flush()
        logging.debug('flushed %s', size)
        self.audio.stream.start_stream()

    @Slot()
    def finishRecording(self):
        self.audio.stream.stop_stream()
        data = self.read_audio(drop_last=3, drop_first=3)
        if self.window.property('scriptFilename'):
            self.deleteFile(self.window.property('scriptFilename'))
        scriptText = self.window.property('scriptText')
        scriptId = self.window.property('scriptId')
        filename = os.path.normpath(os.path.join(self.window.property('saveDir'), "recorder_" + re.sub('\\s','_',scriptId) + '_' + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".wav"))
        self.window.setProperty('scriptFilename', filename)
        self.audio.write_wav(filename, data)
        with open(os.path.join(self.window.property('saveDir'), "recorder.tsv"), "a") as xsvfile:
            xsvfile.write('\t'.join([filename, '0', self.window.property('promptsName'), scriptId, self.sanitize_script(scriptText)]) + '\n')
        logging.debug("wrote %s to %s", len(data), filename)

    @Slot(str)
    def playFile(self, filename):
        winsound.PlaySound(filename, winsound.SND_FILENAME)

    @Slot(str)
    def deleteFile(self, filename):
        os.remove(filename)
        xsvfile_in_path = os.path.join(self.window.property('saveDir'), "recorder.tsv")
        xsvfile_out_path = os.path.join(self.window.property('saveDir'), "recorder_delete_temp.tsv")
        with open(xsvfile_in_path, "r") as xsvfile_in:
            with open(xsvfile_out_path, "w") as xsvfile_out:
                for line in xsvfile_in:
                    if filename not in line:
                        xsvfile_out.write(line)
        os.replace(xsvfile_out_path, xsvfile_in_path)
        self.window.setProperty('scriptFilename', '')

    def read_audio(self, drop_last=None, drop_first=None):
        blocks = []
        while not self.audio.buffer_queue.empty():
            block = self.audio.buffer_queue.get_nowait()
            # logging.debug('read %s', len(block) if block else None)
            if block:
                blocks.append(block)
        # logging.debug('read total %s', len(b''.join(blocks)))
        if drop_last:
            blocks = blocks[:-drop_last]
        if drop_first:
            blocks = blocks[drop_first:]
        return b''.join(blocks)

    def flush(self):
        size = self.audio.buffer_queue.qsize()
        while not self.audio.buffer_queue.empty():
            self.audio.buffer_queue.get_nowait()
        return size

    def get_scripts_from_file(self, n, filename, ordered=False, split_len=None, new_only=False):
        def script_filter(script):
            # match = re.fullmatch(r'\w+ "(.*)"', script)
            patterns = [
                r'^(\w+) "(.*)"$',  # tacspeak_readyornot
            ]
            for pat in patterns:
                script_id = re.sub(pat, r'\1', script, count=1)
                script = re.sub(pat, r'\2', script, count=1)
            return (script_id, script)

        with open(filename, 'r') as file:
            scripts = [line.strip() for line in file if not line.startswith(';')]
        if new_only:
            recorded_ids = self.list_recorded_ids(self.save_dir)
            def id_filter(s):
                for r_id in recorded_ids:
                    if r_id in s:
                        return False
                return True
            filtered_scripts = list(filter(id_filter, scripts))
            scripts = filtered_scripts

        if n is None: n = len(scripts)
        if not ordered:
            # random.shuffle(scripts)
            scripts = [random.choice(scripts) for _ in range(n)]
        scripts = scripts[:n]
        scripts = [script_filter(script) for script in scripts]
        if split_len is not None:
            scripts = [self.split_script(script, split_len) for script in scripts]
            scripts = sum(scripts, [])
        return scripts[:n]

    @classmethod
    def sanitize_script(cls, script):
        return script.strip()
        script = re.sub(r'[\-]', ' ', script)
        script = re.sub(r'[,.?!:;"]', '', script)

    @classmethod
    def split_script(cls, script, split_len):
        scripts = []
        n = math.ceil(len(script) / split_len)
        startpos = 0
        # print(script)
        regex = re.compile(r'\s+')
        for i in range(n):
            match = regex.search(script, pos=startpos+split_len)
            endpos = match.start() if match else None
            scripts.append(script[startpos:endpos].strip())
            # print(startpos, endpos, scripts)
            if endpos is None: break
            startpos = endpos
        return scripts

def main():
    current_path = os.path.abspath(os.path.dirname(__file__))
    qml_file = os.path.join(current_path, os.path.splitext(__file__)[0]+'.qml')

    parser = argparse.ArgumentParser(description='''
        Given a text file containing prompts, this app will choose a random selection
        and ordering of them, display them to be dictated by the user, and record the
        dictation audio and metadata to a `.wav` file and `recorder.tsv` file
        respectively.
    ''')
    parser.add_argument('-p', '--prompts_filename', help='file containing prompts to choose from')
    parser.add_argument('-d', '--save_dir', default='../audio_data', help='where to save .wav & recorder.tsv files (default: %(default)s)')
    parser.add_argument('-c', '--prompts_count', type=int, default=100, help='number of prompts to select and display (default: %(default)s)')
    parser.add_argument('-l', '--prompt_len_soft_max', type=int)
    parser.add_argument('-o', '--ordered', action='store_true', default=False, help='present prompts in order, as opposed to random (default: %(default)s)')
    parser.add_argument('-n', '--new_only', action='store_true', default=False, help='present only prompts that have not previously been recorded (default: %(default)s)')
    args = parser.parse_args()
    assert args.prompts_filename

    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    engine.addImportPath(current_path)
    kwargs = { k: v for k, v in vars(args).items() if v is not None and k in 'prompts_count prompt_len_soft_max'.split() }
    recorder = Recorder(args.save_dir, args.prompts_filename, args.ordered, args.new_only, **kwargs)
    engine.rootContext().setContextProperty('recorder', recorder)
    engine.load(qml_file)
    recorder.window = engine.rootObjects()[0]

    res = app.exec()
    sys.exit(res)

if __name__ == '__main__':
    logging.basicConfig(level=10)
    main()
