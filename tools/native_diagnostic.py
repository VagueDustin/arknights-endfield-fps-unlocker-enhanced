"""Prepare, install, collect, or restore one logged native compatibility test."""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import shutil
import datetime
import native_neural

ROOT=Path(__file__).resolve().parents[1]
LAB=ROOT/'build/native-diagnostic'
GAME=Path(r'C:\Program Files\Epic Games\ArknightsEndfieldgowoU\games\EndField Game')
LOG='FateEngine-native-diagnostic.log'

def prepare():
    source=ROOT/'build/native-preview/package/native-nr'
    target=LAB/'payload';target.mkdir(parents=True,exist_ok=True)
    for name in native_neural.FILES:shutil.copy2(source/name,target/name)
    config=configparser.ConfigParser(interpolation=None);config.optionxform=str
    config.read(target/'OptiScaler.ini')
    for key,value in {'LogToFile':'true','LogLevel':'1','LogAsync':'false','LogFileName':LOG,'OpenConsole':'false'}.items():config['Log'][key]=value
    config['Hotfix']['CheckForUpdate']='false'
    config['DlssNr']['Enabled']='false'
    config['FateDiagnostics']={'StartupTrace':'1'}
    with (target/'OptiScaler.ini').open('w') as stream:config.write(stream)
    manifest={'files':{name:hashlib.sha256((target/name).read_bytes()).hexdigest() for name in native_neural.FILES}}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Prepared diagnostic payload. NR starts off; synchronous logging enabled. Game unchanged.')

def collect():
    target=LAB/('capture-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));target.mkdir(parents=True)
    sources=[GAME/LOG,GAME/'FateEngine-startup-trace.log',GAME/'OptiScaler.ini',GAME/native_neural.STATE,
             Path.home()/'AppData/LocalLow/Gryphline/Endfield/Player.log']
    sources.extend(GAME.glob('FateEngine-startup-trace-*.log'))
    for source in sources:
        if source.is_file():shutil.copy2(source,target/source.name)
    print('Evidence saved: '+str(target))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','install','collect','restore']);args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='install':print(native_neural.install(GAME,LAB/'payload'))
    elif args.action=='collect':collect()
    else:
        collect()
        print(native_neural.restore(GAME))
