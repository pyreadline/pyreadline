# Must be launched with the build version of pyreadline on path
#
import re,os
import pyreadline.release as release

def run_shell_command(command,path="",stdin=""):
    """command= commandline, don't forget to qoute paths with spaces
    path=path to change to before issuing command
    stdin=string    string to pass in as standard input
    """
    oldpath=os.getcwd()
    if path:
        os.chdir(path)
    (sin,sout,serr)=os.popen3(command)
    if stdin:
        sin.write(stdin)
        sin.close()
    txt=sout.read()
    errtxt=serr.read()
    sout.close()
    serr.close()
    os.chdir(oldpath)
    return txt,errtxt

def build_pdf_doc():
    print "latex pass 1"
    t,err=run_shell_command("pdflatex -interaction=batchmode manual.tex")
    print "latex pass 2"
    t,err=run_shell_command("pdflatex -interaction=batchmode manual.tex")
    print "removing tempfiles files"
    for ext in ["aux","log","out","toc"]:
        os.remove("manual.%s"%ext)


fil=open("manual_base.tex")
txt=fil.read()
fil.close()

manualtext=re.sub("--version--",release.version,txt)
fil=open("manual.tex","w")
fil.write(manualtext)
fil.close()
print "Manual (manual.tex) succesfully updated, exiting..."
print "Run pdflatex manual.tex manually to see errors"
build_pdf_doc()
