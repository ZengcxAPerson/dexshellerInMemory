# -*- coding: UTF-8 -*- 

import struct
import zlib
import hashlib
import re
from subprocess import check_call
import argparse
import os
from xml.dom.minidom import parse
import xml.dom.minidom
import zipfile
from PIL import Image
import shutil


stApkToolPt = r'D:\Tools\ReverseTools\android\apktool_2.4.1.jar'
stShellAppPt = r'.\shellApplicationSourceCode'
staaptPt = r'D:\Android\Sdk\build-tools\29.0.3\aapt.exe'
stAndroidJarlibPt = r'D:\Android\Sdk\platforms\android-29\android.jar'
stdxJarPt = r'D:\Android\Sdk\build-tools\29.0.3\lib\dx.jar'
stApksignJarPt = r'D:\Android\Sdk\build-tools\29.0.3\lib\apksigner.jar'
stCurrentPt = os.path.abspath(__file__).replace(os.path.basename(__file__), "")


def add_srcDexToShellDex(srcDex, shellDex):

    liShellDt = []
    liSrcDexDt = []
    liAllDt = []

    #将原始DEX和壳DEX数据放在一个列表中
    with open(shellDex, "rb") as f:
        shellData = f.read()
        liShellDt = list(struct.unpack(len(shellData)*'B', shellData))
    with open(srcDex, 'rb') as f:
        srcDt = f.read()
        liSrcDexDt = list(struct.unpack(len(srcDt)*'B', srcDt))
    liAllDt.extend(shellData)
    # 加密原DEX
    for i in liSrcDexDt:  
        liAllDt.append(i ^ 0xff)

    iSrcDexLen = len(liSrcDexDt)
    liSrcDexLen = intToSmalEndian(iSrcDexLen)
    liSrcDexLen.reverse()
    # 加密原DEX长度
    for i in liSrcDexLen:
        liAllDt.append(i ^ 0xff)

    # 计算合成后DEX文件的checksum、signature、file_size
    # 更改文件头
    newFsize = len(liAllDt)
    liNewFSize = intToSmalEndian(newFsize)
    for i in range(4):
        liAllDt[32 + i] = liNewFSize[i]

    newSignature = hashlib.sha1(bytes(liAllDt[32:])).hexdigest()
    liNewSignature = re.findall(r'.{2}', newSignature)
    for i in range(len(liNewSignature)):
        liNewSignature[i] = ord(bytes.fromhex(liNewSignature[i]))
    for i in range(20):
        liAllDt[12 + i] = liNewSignature[i]

    newChecksum = zlib.adler32(bytes(liAllDt[12:]))
    liNewChecksum = intToSmalEndian(newChecksum)
    for i in range(4):
        liAllDt[8 + i] = liNewChecksum[i]
    
    with open(os.path.join(stCurrentPt, 'classes.dex'), 'wb') as f:
        f.write(bytes(liAllDt))


def intToSmalEndian(numb):
    liRes = []

    stHexNumb = hex(numb)[2:]
    for i in range(8 - len(stHexNumb)):
        stHexNumb = '0' + stHexNumb
    liRes = re.findall(r'.{2}', stHexNumb)
    for i in range(len(liRes)):
        liRes[i] = ord(bytes.fromhex(liRes[i]))
    liRes.reverse()

    return liRes

def decompAPK(fp):
    cmd = []
    cmd.append('java')
    cmd.append('-jar')
    cmd.append(stApkToolPt)
    cmd.append('d')
    cmd.append('-o')
    cmd.append(fp + "decompile")
    cmd.append(fp)
    check_call(cmd)
 
def getAppName(fp):
    stAppName = "android.app.Application"
    stDisassembleDp = fp + "decompile"
    stAMFp = os.path.join(stDisassembleDp, "AndroidManifest.xml")
    oDomTree = parse(stAMFp)
    manifest = oDomTree.documentElement
    apps = manifest.getElementsByTagName('application')

    if len(apps) != 1:
        print("存在多个Application")
        raise(Exception)
    if apps[0].getAttribute("android:name") != "":
        stAppName = apps[0].getAttribute("android:name")
    
    return stAppName
    
def replaceTag(fp, stValue):
    stAXMLFp = os.path.join(stCurrentPt, fp + "decompile", "AndroidManifest.xml")
    dom = None
    with open(stAXMLFp, 'r', encoding='UTF-8') as f:
        dom = parse(f)
    root = dom.documentElement
    app = root.getElementsByTagName('application')[0]
    app.setAttribute("android:name", stValue)
    with open(stAXMLFp, "w", encoding='UTF-8') as f:
        dom.writexml(f, encoding='UTF-8')
    stDecompDp = os.path.join(stCurrentPt, fp + "decompile")
    # 修复PNG文件BUG

    PngBug(stDecompDp)
    cmd = []
    cmd.append('java')
    cmd.append('-jar')
    cmd.append(stApkToolPt)
    cmd.append('b')
    cmd.append('-o')
    cmd.append("result.apk")
    cmd.append(stDecompDp)
    check_call(cmd) 

    shutil.rmtree(stDecompDp)


def save_appName(appName):
    stCfgFp = os.path.join(stShellAppPt, "java/cn/yongye/nativeshell/common/Config.java")
    with open(stCfgFp, 'w') as f:
        f.write("package cn.yongye.nativeshell.common;\n")
        f.write("\n")
        f.write("public class Config {\n")
        f.write("    public static final String MAIN_APPLICATION = \"{}\";\n".format(appName))
        f.write("}")

def compileSrcApk(dp):
    cmd = []
    cmd.append('java')
    cmd.append('-jar')
    cmd.append(stApkToolPt)
    cmd.append('b')
    cmd.append('-f')
    cmd.append('-o')
    cmd.append(stCurrentPt + "\src.apk")
    cmd.append(dp)
    check_call(cmd)

def compileShellDex():

    licmd2 = []
    licmd2.append("javac")
    licmd2.append("-encoding")
    licmd2.append("UTF-8")
    licmd2.append("-target")
    licmd2.append("1.8")
    licmd2.append("-bootclasspath")
    licmd2.append(stAndroidJarlibPt)
    licmd2.append("-d")
    licmd2.append(stCurrentPt)
    licmd2.append(stCurrentPt + r"\shellApplicationSourceCode\java\cn\yongye\nativeshell\*.java")
    licmd2.append(stCurrentPt + r"\shellApplicationSourceCode\java\cn\yongye\nativeshell\common\*.java")
    licmd2.append(stCurrentPt + r"\shellApplicationSourceCode\java\cn\yongye\nativeshell\inmemoryloaddex\*.java")
    check_call(licmd2)

    licmd3 = []
    licmd3.append("java")
    licmd3.append("-jar")
    licmd3.append(stdxJarPt)
    licmd3.append("--dex")
    licmd3.append("--output=" + stCurrentPt + "\shell.dex")
    licmd3.append(r"cn\yongye\nativeshell\*.class")
    licmd3.append(r"cn\yongye\nativeshell\common\*.class")
    licmd3.append(r"cn\yongye\nativeshell\inmemoryloaddex\*.class")
    check_call(licmd3)

    shutil.rmtree("cn")
    
    
def replaceSDexToShellDex(stSApkFp):
    # 提取原APK中的DEX到本地
    oFApk = zipfile.ZipFile(stSApkFp)
    oFApk.extract("classes.dex", stCurrentPt)
    oFApk.close()
    stSDexFp = os.path.join(stCurrentPt, "classes.dex")
    stShellDexFp = os.path.join(stCurrentPt, "shell.dex")
    # 将原DEX添加到壳DEX尾部，保存到本目录下为classes.dex
    add_srcDexToShellDex(stSDexFp, stShellDexFp)
    #将修改后的壳DEX添加到原DEX中

    cmd1 = []
    cmd1.append(staaptPt)
    cmd1.append("r")
    cmd1.append(stSApkFp)
    cmd1.append("classes.dex")
    check_call(cmd1)

    oNewApk = zipfile.ZipFile(stSApkFp, "a")
    oNewApk.write("classes.dex", "classes.dex")
    oNewApk.close()

    os.remove(stSDexFp)
    os.remove(stShellDexFp)


def signApk(fp, stKeystoreFp):
    cmd = []
    cmd.append("java")
    cmd.append("-jar")
    cmd.append(stApksignJarPt)
    cmd.append("sign")
    cmd.append("--ks")
    cmd.append(stKeystoreFp)
    cmd.append("--ks-pass")
    cmd.append("pass:123456")
    cmd.append(fp)
    check_call(cmd)


def PngBug(decompFp):
    import filetype
    liFiles = os.listdir(decompFp)
    for fn in liFiles:
        fp = os.path.join(decompFp, fn)
        if os.path.isdir(fp):
            PngBug(fp)   
        if fp.endswith(".png") and filetype.guess(fp).MIME == "image/gif":
            im = Image.open(fp)
            current = im.tell()
            im.save(fp)

def addLib(fp):
    stLib2Fp1 = os.path.join(stCurrentPt, "lib", "libdalvik_system_DexFile.so")
    stLib2Fp2 = os.path.join(stCurrentPt, "lib", "libyongyejiagu.so")

    apk = zipfile.ZipFile(fp, "a")
    apk.write(stLib2Fp1, "lib/x86/libdalvik_system_DexFile.so")
    apk.write(stLib2Fp2, "lib/x86/libyongyejiagu.so")
    apk.close()

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help="对指定文件进行加固", nargs=1, metavar='APK')
    args = parser.parse_args()

    if args.f:
        fp = args.__dict__.get('f')[0]
        """
        1. 第一步：确定加密算法
        """
        inKey = 0xFF
        print("[*] 确定加密解密算法，异或: {}".format(str(inKey)))

        """
        2. 第二步：准备好壳App
        """
        # 反编译原apk
        decompAPK(fp)
        # print("[*] 反编译原的apk文件{}完成".format(fp))
        # 获取Applicaiton name并保存到壳App源码中
        stSrcDexAppName = getAppName(fp)
        # print("[*] 获取原apk文件的Application Android:name=\"{}\" 完成".format(stSrcDexAppName))
        save_appName(stSrcDexAppName)
        # print("[*] 保存原apk文件的Application Android:name=\"{}\" 到壳App源码的配置文件完成".format(stSrcDexAppName))
        # 编译出壳DEX
        compileShellDex()
        print("[*] 壳App的class字节码文件编译为:shell.dex完成")

        """
        3. 第三步：修改原apk AndroidManifest.xml文件中的Application name字段为壳的Application name字段
        """
        # 替换壳Applicaiton name到原apk的AndroidManifest.xml内
        replaceTag(fp, "cn.yongye.nativeshell.StubApp")
        print("[*] 原apk文件AndroidManifest.xml中application的name字段替换为壳application name字段完成")
        
        """
        4. 替换原apk中的DEX文件为壳DEX
        """
        replaceSDexToShellDex(os.path.join(stCurrentPt, "result.apk"))
        print("[*] 壳DEX替换原apk包内的DEX文件完成")

        """
        5. 添加脱壳lib库到原apk中
        """
        addLib("result.apk")
        
        """
        6. apk签名
        """
        signApk(os.path.join(stCurrentPt, "result.apk"), os.path.join(stCurrentPt, "demo.keystore"))
        print("[*] 签名完成，生成apk文件: {}".format(os.path.join(stCurrentPt, "result.apk")))
        

    else:
        parser.print_help()
    
    
