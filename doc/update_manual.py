# Must be launched with the build version of pyreadline on path
#
import re
import pyreadline.release as release


fil=open("manual_base.tex")
txt=fil.read()
fil.close()

manualtext=re.sub("--version--",release.version,txt)
fil=open("manual.tex","w")
fil.write(manualtext)
fil.close()
print "Manual (magic.tex, manual.lyx) succesfully updated, exiting..."


