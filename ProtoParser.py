# -*- coding: utf-8 -*-
import collections,sys,struct
reload(sys)
sys.setdefaultencoding('utf-8')

#struct中类型的格式符
smallEndian='<'
tp_int8,tp_uint8='b','B'
tp_int16,tp_uint16='h','H'
tp_int32,tp_uint32='i','I'
tp_bool,tp_float,tp_double='?','f','d'

class ProtoParser:
    def __init__(self):
        self.index=0
        self.index_s=0
        self.textdict=collections.OrderedDict()
    
    #得到数组长度
    def getnums(self,line):
        pos1 = line.find('[')
        if pos1 == -1:
            return 1
        pos2 = line.find(']')
        if pos1==(pos2-1):
            return -1
        else:
            return int(line[pos1+1:pos2])

    #得到变量名
    def getkey(self,line):
        pos=line.find(']')
        if pos==-1:
            pos=0
        s=line[pos+1:]
        s1=s.replace(';','')
        s2=s1.strip()
        return s2


    #得到基础类型和变量名
    def getBaseTypeNumsName(self,line):
        if line.startswith('int8'):
            baseType = 'int8'
        elif line.startswith('uint8'):
            baseType = 'uint8'
        elif line.startswith('int16'):
            baseType = 'int16'
        elif line.startswith('uint16'):
            baseType = 'uint16'
        elif line.startswith('int32'):
            baseType = 'int32'
        elif line.startswith('uint32'):
            baseType = 'uint32'
        elif line.startswith('float'):
            baseType = 'float'
        elif line.startswith('double'):
            baseType = 'double'
        elif line.startswith('bool'):
            baseType = 'bool'
        else:
            baseType = 'string'
        name=self.getkey(line[len(baseType):])
        nums = self.getnums(line)
        v=(baseType,nums,name)
        return v


    #解析一个花括号中的内容，返回一个dict对象
    def getdict(self,text): #text为协议文本，index表示当前要解析的行（非空），从'{'开始
        self.index=self.index+1 #先默认‘{’单独占一行
        tmpdict = collections.OrderedDict()
        while text[self.index].startswith('}')==False:
            value = () #dict中的value，形式为value=(type,nums),type为类型（可能也是一个dict），nums为数组长度，-1表示不定长
            if text[self.index].startswith('{'):#组合类型
                value_1 = self.getdict(text)
                value_2 = self.getnums(text[self.index])#得到数组长度
                key = self.getkey(text[self.index])#key为字段名
            else:#基础类型
                t = self.getBaseTypeNumsName(text[self.index])
                value_1 = t[0]
                value_2 = t[1]
                key = t[2]
            value = (value_1,value_2)
            tmpdict[key]=value
            self.index=self.index+1
        return tmpdict
    
    #处理从文本中读到的一行字符
    def processLine(self,line):
        res = []
        line=line.strip()#去除左右的空格、末尾换行符
        while line!='':
            if line.startswith('{'):#'{'单独做一项
                res.append('{')
                line = line[1:].strip()
            else:#不是'{'开头，寻找第一个';'
                pos = line.find(';')
                if pos==-1:#行中无';'，但不为空，则无字段，只剩下'}'
                    res.append('}')
                    return res
                res.append(line[:(pos+1)])
                line=line[(pos+1):].strip()
        return res

    #从指定的文本文件filename中读取协议描述文本,存为python内部数据，以备解析使用
    def buildDesc(self,filename):
        f=open(filename)
        text = []
        for line in f.readlines():
            text+=(self.processLine(line))
        while '' in text:
            text.remove('')
        #将text中的内容解析为dict
        self.index=0#getdict方法使用前index为0
        self.textdict = self.getdict(text)
    
    #对单个基础类型数据进行编码
    def _codeBaseType(self,tp,data):
        binstr = ''
        fmt = smallEndian
        if tp=='string':
            binstr+=struct.pack(smallEndian+tp_uint16,len(data)).encode("hex")
            binstr+=data.encode("hex")
            return binstr
        elif tp=='int8':
            fmt+=tp_int8
        elif tp=='uint8':
            fmt+=tp_uint8
        elif tp=='int16':
            fmt+=tp_int16
        elif tp=='uint16':
            fmt+=tp_uint16
        elif tp=='int32':
            fmt+=tp_int32
        elif tp=='uint32':
            fmt+=tp_uint32
        elif tp=='float':
            fmt+=tp_float
        elif tp=='double':
            fmt+=tp_double
        elif tp=='bool':
            fmt+=tp_bool
        binstr+=struct.pack(fmt,data).encode("hex")
        return binstr
    
    #对基础类型编码
    def codeBaseType(self,typeInfo,dataInfo):#typeInfo=(type,nums),dataInfo为数据或数据元组
        binstr=''
        tp=typeInfo[0]
        nums=typeInfo[1]
        if nums==-1:
            nums=len(dataInfo)
            binstr+=struct.pack('<H',nums).encode("hex")
        if isinstance(dataInfo,tuple):
            for i in range(len(dataInfo)):
                binstr+=self._codeBaseType(tp,dataInfo[i])
        else:
            binstr+=self._codeBaseType(tp,dataInfo)
        return binstr

    #根据协议描述文本，将字典d序列化为16进制字符串
    def _dumps(self,text,d,lenth):#text为协议描述文本字典，d为待序列化字典,nums表示数组个数
        binstr=''
        isTuple = False
        if lenth==-1:#不定长数组
            lenth = len(d)#若为不定长数组，d应该是个元组,length为元组长度
            isTuple = True#不定长数组对应的应该是元组
            binstr+=struct.pack('<H',lenth).encode("hex")#在字符串中加入长度        
        if lenth==1 and isTuple==False:#d为一个字典，而非元组
            for key in text:
                value = text[key]
                if d.has_key(key)==False or d[key]==None:
                    continue
                if isinstance(value[0],dict):
                    binstr+=self._dumps(value[0],d[key],value[1])
                else:
                    binstr+=self.codeBaseType(value,d[key])
        else:#若长度非1，d应该为一个元组，元组中每个元素都为dict
            for i in range(lenth):
                data = d[i]
                for key in text:
                    value = text[key]#value=(type,nums)
                    if data.has_key(key)==False or data[key]==None:
                        continue
                    if isinstance(value[0],dict):#解析dict
                        binstr+=self._dumps(value[0],data[key],value[1])
                    else:#解析基本类型
                        binstr+=self.codeBaseType(value,data[key])
        return binstr
    
    def dumps(self,obj):
        return self._dumps(self.textdict,obj,1)
    
    #得到长度
    def getLenth(self,s):
        lenth=struct.unpack(smallEndian+tp_uint16,s[self.index_s:self.index_s+4].decode("hex"))
        res = lenth[0]
        self.index_s+=4
        return res
    
    #基础类型解码
    def decodeBaseType(self,tp,s):
        fmt = smallEndian
        index=self.index_s
        if tp == 'string':
            lenth = self.getLenth(s)
            res = s[self.index_s:(self.index_s+2*lenth)].decode("hex")
            self.index_s+=2*lenth
            return res
        elif tp=='int8':
            fmt+=tp_int8
            self.index_s+=2
        elif tp=='uint8':
            fmt+=tp_uint8
            self.index_s+=2
        elif tp=='int16':
            fmt+=tp_int16
            self.index_s+=4
        elif tp=='uint16':
            fmt+=tp_uint16
            self.index_s+=4
        elif tp=='int32':
            fmt+=tp_int32
            self.index_s+=8
        elif tp=='uint32':
            fmt+=tp_uint32
            self.index_s+=8
        elif tp=='float':
            fmt+=tp_float
            self.index_s+=8
        elif tp=='double':
            fmt+=tp_double
            self.index_s+=16
        elif tp=='bool':
            fmt+=tp_bool
            self.index_s+=2
        res = struct.unpack(fmt,s[index:self.index_s].decode("hex"))
        r=res[0]
        return r
    
    #根据协议描述文本，将字符串反序列化为dict对象
    def _loads(self,text,s):#text为协议描述文本字典，s为待反序列化字符串，index_s用来表示当前要解析的位置
        d={}
        for key in text:
            value = text[key]#value=(type,nums)
            tp = value[0]
            nums = value[1]
            isTuple = False#若为不定长数组，类型应该为tuple
            if nums==-1:#变长数组，要从字符串中获取长度
                nums=self.getLenth(s)
                isTuple = True
            v=[]
            if isinstance(tp,dict):
                for i in range(nums):
                    v.append(self._loads(tp,s))
            else:
                for i in range(nums):
                    v.append(self.decodeBaseType(tp,s))
            if len(v)==1 and isTuple==False:
                val = v[0]
            else:
                val = tuple(v)
            d[key] = val
        return d
    
    def loads(self,binstr):
        self.index_s = 0
        return self._loads(self.textdict,binstr)

filename = "a.proto"
a1 = ProtoParser()
a1.buildDesc(filename)
print a1.textdict

obj = {
	"name": "骨精灵",
	"id": 5201314,
	"married": False,
	"friends": (),
	"position": None,
	"pet": {
		"name": "骨精灵的小可爱",
		"skill": (
			{
				"id": 1,
			},
			{
				"id": 2,
			})
	},
    "none":({"n":{}},)
}

binstr = a1.dumps(obj)
print binstr

a2 = ProtoParser()
a2.buildDesc(filename)
result = a2.loads(binstr)

print result
print result['name']