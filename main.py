from sys import argv
import CsbFile
from CsbExporter import Export
from CsbImporter import Import

def main():
    if (len(argv) == 1 or "-h" in argv):
        print("Usage:")
        print("    CollisionSceneBinaryCLI.exe file.csb (arguments)")
        print("    CollisionSceneBinaryCLI.exe file.dae (arguments)")

        print("Arguments:")
        print("    -big (big endian, needed for color splash)")
        print("    -mobj (create as map object)")

        return
    is_big_endian = "-big" in argv
    is_map_object = "-mobj" in argv
    
    for arg in argv[1:]:
        if arg.endswith(".csb"): # export
            print("Exporting CSB file!")
            
            csb = CsbFile.CsbFile(open(arg, "rb").read(), False)
            output = arg[:-4] + ".glb"
            
            Export(csb, output)
            #with open(output, "w") as file:
            #    file.write("")
        elif arg.endswith(".dae"): # import and create
            print("Generating CSB and CTB files!")
            
            output = arg[:-4]
            Import(arg, output, is_big_endian, is_map_object)
    
if __name__ == "__main__":
    main()