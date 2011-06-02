import subprocess
import os
import sys
import shutil
import tarfile
import logging
import getpass
import re
from optparse import OptionParser, OptionGroup
import ConfigParser

from galleryremote import Gallery
from galleryremote.gallery import GalleryException


class MCRenderer(object):
    def __init__(self, config, album_name):
        self.logger = logging.getLogger('mcrender')
        self.config = config
        self.album_name = album_name
        self.to_clean = []
        self.cwd = os.getcwd()
        self.src_dir = config.get('directories', 'source')
        self.img_dir = os.path.join(self.cwd, config.get('directories', 'images'))
        self.obj_dir = os.path.join(self.cwd, config.get('directories', 'objects'))
        self.tgz_dir = os.path.join(self.cwd, config.get('directories', 'raw_backups'))
        self.archive_suffix = config.get('directories', 'backup_suffix')
        self.blender_opts = ["blender"] + \
                            config.get('blender', 'args').split() + \
                            ["-P", config.get('blender', 'render_script')]
        self.mcobj_opts = ["mcobj.exe"] + config.get('mcobj', 'args').split()

        for d in [self.img_dir, self.obj_dir, self.tgz_dir]:
            if not os.path.exists(d):
                os.mkdir(d)

    def copy(self, tarball):
        if not os.path.exists(self.src_dir):
            self.logger.critical("No %s to copy from!", self.src_dir)
            sys.exit(1)

        self.logger.info("Copying %s to %s", tarball, self.tgz_dir)
        shutil.copy(os.path.join(self.src_dir, tarball), self.tgz_dir)

    def expand(self):
        tarball = victim + self.archive_suffix
        fqp_tarball = os.path.join(self.tgz_dir, tarball)
        if not os.path.exists(fqp_tarball):
            self.copy(tarball)

        self.logger.debug("Expanding into " + self.cwd)
        tf = tarfile.open(fqp_tarball)
        tf.extractall()

        self.to_clean = ['extracted']

    def create_obj(self):
        mtl = os.path.join(self.obj_dir, self.victim + ".mtl")
        if os.path.exists(self.obj_file) and os.path.exists(mtl):
            self.logger.debug("Found pre-computed object!")
            shutil.move(self.obj_file, self.cwd)
            shutil.move(mtl, self.cwd)
        else:
            if not os.path.exists(os.path.join(self.cwd, self.victim)):
                self.expand()

            self.logger.debug("Converting map into 3D object")
            rc = subprocess.call(self.mcobj_opts + ["-o", self.obj_file,
                                                    self.victim])
            if rc:
                self.logger.critical("mcobj exited with rc = " + rc)
                sys.exit(rc)

        self.to_clean.append('obj_files')

    def render_image(self):
        self.obj_file = self.victim + ".obj"
        self.fqpn_obj_file = os.path.join(self.obj_dir, self.obj_file)
        if not os.path.exists(os.path.join(self.cwd, self.obj_file)):
            self.create_obj()

        self.logger.info("Converting 3D object into PNG")
        rc = subprocess.call(self.blender_opts + [self.obj_file])
        if rc:
            self.logger.critical("blender exited with rc = " + rc)
            sys.exit(rc)
        else:
            shutil.move(self.victim + ".png", self.img_dir)

    def upload_image(self, g, victim):
        self.to_clean = []
        self.victim = victim
        current_images = [img['title'] for img in
                              g.fetch_album_images(self.album_name)]

        img_file = self.victim + ".png"
        if img_file in current_images:
            self.logger.info("%s already in Gallery!", img_file)
            self.cleanup()
            return

        final_file = os.path.join(self.img_dir, img_file)
        if not os.path.exists(final_file):
            self.render_image()

        self.logger.debug("Uploading")
        g.add_item(album_name, final_file, self.victim, self.victim)

        self.cleanup()

    def cleanup(self):
        if 'extracted' in self.to_clean:
            self.logger.debug("Cleaning up expanded map")
            shutil.rmtree(os.path.join(self.cwd, victim))

        if 'obj_files' in self.to_clean:
            self.logger.debug("Cleaning up OBJ/MTL files")
            shutil.move(victim + ".obj", self.obj_dir)
            shutil.move(victim + ".mtl", self.obj_dir)

# <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
# <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>
# <><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><><>

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--config", dest="conf_file",
            default=os.path.join(os.getcwd(), "config.ini"),
            help="The config file to use [default: %default]")
    parser.add_option("-d", "--debug", dest="debug",
            default=False, action="store_true",
            help="Turns on debugging (lots of debugging!) [default: %default]")

    (opts, args) = parser.parse_args()

    if not os.path.exists(opts.conf_file):
        parser.error("Config file (%s) doesn't exist!" % opts.conf_file)

    conf = ConfigParser.ConfigParser()
    conf.read(opts.conf_file)

    logger = logging.getLogger('mcrender')
    logger.propagate = False

    if opts.debug:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    console_handler = logging.StreamHandler()

    formatter = logging.Formatter('%(asctime)s:%(levelname)8s:%(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging_level)

    if conf.getboolean('gallery2', 'enabled'):
        logger.debug("Logging into gallery")
        g = Gallery(conf.get('gallery2', 'url'))
        g.login(conf.get('gallery2', 'user'),
                conf.get('gallery2', 'password'))

    logger.debug("Finding our album")
    albums = g.fetch_albums_prune()
    our_album = conf.get('gallery2', 'albumname').lower()
    candidate_albums = [k for k,v in albums.iteritems()
                            if v['title'].lower() == our_album]

    if not candidate_albums:
        logger.critical("Couldn't find a %s album!", our_album)
        sys.exit(1)

    album_name = candidate_albums[0]

    if args:
        to_work = args
    else:
        file_re = re.compile(conf.get('directories', 'backup_regex'))
        candidates = set(f.split(".")[0] for f in
                             os.listdir(conf.get('directories', 'source'))
                                if re.match(file_re, f))
        logger.debug("Found %d candidates", len(candidates))
        finished = set(img['title'].replace('.png', '') for img in
                           g.fetch_album_images(album_name))
        logger.debug("Found %d finished images", len(finished))
        to_work = sorted(list(candidates - finished))

    if len(to_work) == 0:
        logger.info("All caught up, nothing to do!")
        sys.exit(0)

    logger.info("Have %d maps to work on: %s", len(to_work), ", ".join(to_work))

    renderer = MCRenderer(conf, album_name)

    for victim in to_work:
        logger.info("Starting on " + victim)
        renderer.upload_image(g, victim)
