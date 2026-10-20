"""python3 -m unittest catio/tools/test_build_art.py

The one thing here worth a test: which zip is which pack is read from what is inside it, so neither the
zips' names nor the order they are given in matters. CLAUDE.md used to have to warn that the order did.
Drawing the art needs the packs themselves, which their licences keep out of git, so that isn't tested."""
import contextlib
import importlib.util
import io
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))   # build-art imports furniture and manor as siblings
_spec = importlib.util.spec_from_file_location("build_art", TOOLS / "build-art.py")
build_art = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_art)

# What each pack looks like from the outside: the file build-art knows it by, under the folder the real zip
# keeps it in, which is also what proves the match isn't anchored at the start of the name.
INSIDE = {
    "cabin": "CosyCabin/CosyCabin_Objects.png",
    "cats": "CatMegaFree/MochiFree/Idle.png",
    "garden": "Top down Garden Castle.png",
    "wood": "Wood Garden Asset Pack/White fence/White-fence-2.png",
    "stone": "Pixel Art Top Down - Basic/Texture/TX Props.png",
    "sprout": "Sprout Lands - UI Pack/Sprite sheet for Basic Pack.png",
    "dreamy": "Little Dreamyland - Free Pack/Tileset/Nature_Tileset.png",
    "pastel": "Game_UI_Pack_Pastel/PNG/Filled/Icons/Books/Book_Filled_Indigo.png",
}
# The two packs no signature names: they are only ever read through load(), which searches every zip.
UNSIGNED = {"plants.zip": "Tileset/House_Tileset.png",
            "sprites.zip": "Objects/Basic_Grass_Biom_things.png"}


def quietly(f, *a):
    """identify() prints what it took for what; the tests don't need to read it."""
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a)


class Identify(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)

    def zip_at(self, name, members):
        at = self.dir / name
        with zipfile.ZipFile(at, "w") as z:
            for m in members:
                z.writestr(m, b"")
            z.writestr("Licence.txt", b"")   # every pack has one: nothing may be recognised by it
        return at

    def her_drive_folder(self):
        """The ten zips, under names that say nothing about which pack or what order."""
        for key, inside in INSIDE.items():
            self.zip_at(key + "-pack.zip", [inside])
        for name, inside in UNSIGNED.items():
            self.zip_at(name, [inside])
        return self.dir

    def test_a_folder_names_every_pack(self):
        paths = build_art.find_zips([str(self.her_drive_folder())])
        self.assertEqual(len(paths), 10)
        pack, zips = quietly(build_art.identify, paths)
        self.assertEqual(set(pack), set(build_art.SIGNATURE))
        for key in build_art.SIGNATURE:
            self.assertEqual(pack[key].name, key + "-pack.zip")
        self.assertEqual(len(zips), 10, "every zip is searched by load(), named or not")

    def test_neither_the_names_nor_the_order_matter(self):
        paths = build_art.find_zips([str(self.her_drive_folder())])
        shuffled = list(reversed(paths))
        self.assertEqual({k: v.name for k, v in quietly(build_art.identify, paths)[0].items()},
                         {k: v.name for k, v in quietly(build_art.identify, shuffled)[0].items()})

    def test_the_named_packs_are_searched_first_in_the_documented_order(self):
        paths = build_art.find_zips([str(self.her_drive_folder())])
        _, zips = quietly(build_art.identify, list(reversed(paths)))
        named = [Path(z.filename).name for z in zips][:len(build_art.SIGNATURE)]
        self.assertEqual(named, [k + "-pack.zip" for k in build_art.SIGNATURE])
        self.assertEqual(sorted(Path(z.filename).name for z in zips[len(build_art.SIGNATURE):]),
                         sorted(UNSIGNED))

    def test_a_zip_is_read_once_however_often_it_is_named(self):
        folder = self.her_drive_folder()
        paths = build_art.find_zips([str(folder), str(folder / "cats-pack.zip"), str(folder)])
        self.assertEqual(len(paths), 10)

    def test_the_sprout_pack_alone_is_the_interface_alone(self):
        only = self.zip_at("anything.zip", [INSIDE["sprout"]])
        pack, zips = quietly(build_art.identify, build_art.find_zips([str(only)]))
        self.assertEqual(set(pack), {"sprout"})
        self.assertEqual([k for k in build_art.SIGNATURE if k not in pack],
                         [k for k in build_art.SIGNATURE if k != "sprout"])

    def test_a_pack_that_isnt_there_is_simply_missing(self):
        folder = self.her_drive_folder()
        (folder / "wood-pack.zip").unlink()
        pack, _ = quietly(build_art.identify, build_art.find_zips([str(folder)]))
        self.assertNotIn("wood", pack)
        self.assertIn("stone", pack, "one pack missing doesn't shift the others along")

    def test_one_zip_is_only_ever_one_pack(self):
        """A zip holding two packs' signatures fills the first and isn't handed out twice."""
        self.zip_at("both.zip", [INSIDE["cabin"], INSIDE["wood"]])
        pack, _ = quietly(build_art.identify, build_art.find_zips([str(self.dir)]))
        self.assertEqual(pack["cabin"].name, "both.zip")
        self.assertNotIn("wood", pack)


if __name__ == "__main__":
    unittest.main()
