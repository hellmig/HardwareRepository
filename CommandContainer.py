"""CommandContainer module

Classes:
- CommandContainer, a special mixin class to be used with
Hardware Objects. It defines a container
for command launchers and channels (see Command package).
- C*Object, command launcher & channel base class
"""

__author__ = 'Matias Guijarro'
__version__ = 1.0

import types
import weakref
import logging
from .dispatcher import *


class ConnectionError(Exception):
    pass


class CommandObject:
    def __init__(self, name, username = None, **kwargs):
        self._name = name 
        self._username = username
        self._arguments = []
        self._combo_arguments_items = {}


    def name(self):
	return self._name

 
    def connectSignal(self, signalName, callableFunc):
        try:
            dispatcher.disconnect(callableFunc, signalName, self) 
        except:
            pass
        dispatcher.connect(callableFunc, signalName, self)

  
    def emit(self, signal, *args):
        signal =  str(signal)

        if len(args) == 1:
            if type(args[0]) == types.TupleType:
                args = args[0]

        dispatcher.send(signal, self, *args) 
      
 
    def addArgument(self, argName, argType, combo_items=None, onchange=None, valuefrom=None):
        #print "Adding argument", argName, argType.lower(), combo_items
        self._arguments.append( (argName, argType.lower(), onchange, valuefrom) )
        if combo_items is not None:
            self._combo_arguments_items[argName]=combo_items


    def getArguments(self):
        return self._arguments


    def getComboArgumentItems(self, argName):
        #print  self._combo_arguments_items[argName]
        return self._combo_arguments_items[argName]
        

    def userName(self):
        return self._username or str(self.name())
    
        
    def isConnected(self):
        return False


class ChannelObject:
    def __init__(self, name, username = None, **kwargs):
        self._name = name
        self._username = username
	self._attributes = kwargs
        self.__firstUpdate=True

    def name(self):
	return self._name

    def connectSignal(self, signalName, callableFunc):
        try:
            dispatcher.disconnect(callableFunc, signalName, self) 
        except:
            pass
        dispatcher.connect(callableFunc, signalName, self)

    def disconnectSignal(self, signalName, callableFunc):
        try:
            dispatcher.disconnect(callableFunc, signalName, self) 
        except:
            pass

    def connectNotify(self, signal):
        if signal == 'update' and self.isConnected():
           self.emit(signal, self.getValue())

    def emit(self, signal, *args):
        signal =  str(signal)

        if len(args) == 1:
            if type(args[0]) == types.TupleType:
                args = args[0]

        dispatcher.send(signal, self, *args)


    def userName(self):
        return self._username or str(self.name())
    

    def isConnected(self):
        return False


    def update(self, value):
        if self.__firstUpdate:
           self.__firstUpdate=False
           return

        if self._onchange is not None:
           cmd, container_ref = self._onchange
           container = container_ref()
           if container is not None:
              cmdobj = container.getCommandObject(cmd)
              if cmdobj is not None:
                 cmdobj(value)
    

    def getValue(self):
        raise NotImplementedError
        

class CommandContainer:
    """Mixin class for generic command and channel containers"""       
    def __init__(self):
        self.__commands = {}
        self.__channels = {}
        self.__commandsToAdd = []
        self.__channelsToAdd = []


    def __getattr__(self, attr):
        try:
            return self.__commands[attr]
        except KeyError:
            raise AttributeError, attr
        
    
    def getChannelObject(self, channelName):
        return self.__channels[channelName]
        

    def getChannelNamesList(self):
        return self.__channels.keys()
        

    def addChannel(self, attributesDict, channel, addNow=True):
        if not addNow:
            self.__channelsToAdd.append( (attributesDict, channel) )
            return
        channelName = attributesDict['name']
        channelType = attributesDict['type']
        channelOnChange = attributesDict.get("onchange", None)
        if channelOnChange is not None:
           del attributesDict['onchange']
        channelValueFrom = attributesDict.get("valuefrom", None)
        if channelValueFrom is not None:
           del attributesDict['valuefrom']
        channelValueFrom = attributesDict.get("valuefrom", None)
        del attributesDict['name']
        del attributesDict['type']

        newChannel = None

        if channelType.lower() == 'spec':
            if not 'version' in attributesDict:
                try:
                    attributesDict['version'] = self.specversion
                except AttributeError:
                    pass

            try:
                from Command.Spec import SpecChannel
                newChannel = SpecChannel(channelName, channel, **attributesDict)
            except:
                logging.getLogger().error('%s: cannot add channel %s (hint: check attributes)', self.name(), channelName)
        elif channelType.lower() == 'taco':
            if not 'taconame' in attributesDict:
                try:
                    attributesDict['taconame']=self.taconame
                except AttributeError:
                    pass

            try:
                from Command.Taco import TacoChannel
                newChannel = TacoChannel(channelName, channel, **attributesDict)
            except:
                logging.getLogger().error('%s: cannot add channel %s (hint: check attributes)', self.name(), channelName)
        elif channelType.lower() == 'tango':
            if not 'tangoname' in attributesDict:
                try:
                    attributesDict['tangoname'] = self.tangoname
                except AttributeError:
                    pass

            try:
                from Command.Tango import TangoChannel
                newChannel = TangoChannel(channelName, channel, **attributesDict)
            except ConnectionError:
                logging.getLogger().error('%s: could not connect to device server %s (hint: is it running ?)', self.name(), attributesDict["tangoname"])
                raise ConnectionError
            except:
                logging.getLogger().exception('%s: cannot add channel %s (hint: check attributes)', self.name(), channelName)
        elif channelType.lower() == "exporter":
            if not 'exporter_address' in attributesDict:
              try:
                attributesDict['exporter_address'] = self.exporter_address
              except AttributeError:
                pass
            host, port = attributesDict["exporter_address"].split(":")

            try:
              attributesDict["address"] = host
              attributesDict["port"] = int(port)
              del attributesDict["exporter_address"]

              from Command.Exporter import ExporterChannel
              newChannel = ExporterChannel(channelName, channel, **attributesDict)
            except:
              logging.getLogger().exception('%s: cannot add channel %s (hint: check attributes)', self.name(), channelName)
            
        if newChannel is not None:
            if channelOnChange is not None:
               newChannel._onchange = (channelOnChange, weakref.ref(self))
            else:
               newChannel._onchange = None
            if channelValueFrom is not None:
               newChannel._valuefrom = (channelValueFrom, weakref.ref(self))
            else:
               newChannel._valuefrom = None

            self.__channels[channelName] = newChannel

            return newChannel

         
    def setValue(self, channelName, value):
        self.__channels[channelName].setValue(value)


    def getValue(self, channelName):
        return self.__channels[channelName].getValue()


    def getChannels(self):
        for chan in self.__channels.itervalues():
            yield chan
            
    
    def getCommandObject(self, cmdName):
        return self.__commands[cmdName]
        

    def getCommands(self):
        for cmd in self.__commands.itervalues():
            yield cmd
        
    
    def getCommandNamesList(self):
        return self.__commands.keys()
        

    def addCommand(self, arg1, arg2 = None, addNow=True):
        if not addNow:
            self.__commandsToAdd.append( (arg1, arg2) )
            return
        newCommand = None
        
        if type(arg1) == types.DictType:
            attributesDict = arg1
            cmd = arg2
        
            cmdName = attributesDict['name']
            cmdType = attributesDict['type']
            del attributesDict['name']
            del attributesDict['type']
        else:
            attributesDict = {}
            attributesDict.update(arg1.getProperties())

            try:
                cmdName = attributesDict['name']
                cmdType = attributesDict['type']
                cmd = attributesDict['toexecute']
            except KeyError, err:
                logging.getLogger().error('%s: cannot add command: missing "%s" property', self.name(), err.args[0])
                return
            else:
                del attributesDict['name']
                del attributesDict['type']
                del attributesDict['toexecute']
        
        
        if cmdType.lower() == 'spec':
            if not 'version' in attributesDict:
                try:
                    attributesDict['version'] = self.specversion
                except AttributeError:
                    pass

            try:
                from Command.Spec import SpecCommand
                newCommand = SpecCommand(cmdName, cmd, **attributesDict)
            except:
                logging.getLogger().exception('%s: could not add command "%s" (hint: check command attributes)', self.name(), cmdName)
        elif cmdType.lower() == 'taco':
            if not 'taconame' in attributesDict:
                try:
                    attributesDict['taconame'] = self.taconame
                except AttributeError:
                    pass

            try:
                from Command.Taco import TacoCommand
                newCommand = TacoCommand(cmdName, cmd, **attributesDict)
            except:
                logging.getLogger().exception('%s: could not add command "%s" (hint: check command attributes)', self.name(), cmdName)
        elif cmdType.lower() == 'tango':
            if not 'tangoname' in attributesDict:
                try:
                    attributesDict['tangoname'] = self.tangoname
                except AttributeError:
                    pass
            try:
                from Command.Tango import TangoCommand
                newCommand = TangoCommand(cmdName, cmd, **attributesDict)
            except ConnectionError:
                logging.getLogger().error('%s: could not connect to device server %s (hint: is it running ?)', self.name(), attributesDict["tangoname"])
                raise ConnectionError
            except:
                logging.getLogger().exception('%s: could not add command "%s" (hint: check command attributes)', self.name(), cmdName)
        elif cmdType.lower() == 'exporter':
            if not 'exporter_address' in attributesDict:
              try:
                attributesDict['exporter_address'] = self.exporter_address
              except AttributeError:
                pass
            host, port = attributesDict["exporter_address"].split(":")

            try:
              attributesDict["address"] = host
              attributesDict["port"] = int(port)
              del attributesDict["exporter_address"]

              from Command.Exporter import ExporterCommand
              newCommand = ExporterCommand(cmdName, cmd, **attributesDict)
            except:
              logging.getLogger().exception('%s: cannot add command %s (hint: check attributes)', self.name(), commandName)
        elif cmdType.lower() == 'pool':
            if not 'tangoname' in attributesDict:
                try:
                    attributesDict['tangoname'] = self.tangoname
                except AttributeError:
                    pass
            try:
                from Command.Pool import PoolCommand
                newCommand = PoolCommand(cmdName, cmd, **attributesDict)
            except ConnectionError:
                logging.getLogger().error('%s: could not connect to device server %s (hint: is it running ?)', self.name(), attributesDict["tangoname"])
                raise ConnectionError
            except:
                logging.getLogger().exception('%s: could not add command "%s" (hint: check command attributes)', self.name(), cmdName)
                
        if newCommand is not None:
            self.__commands[cmdName] = newCommand

            if not type(arg1) == types.DictType:
                i = 1
                for arg in arg1.getObjects('argument'):
                    onchange=arg.getProperty("onchange")
                    if onchange is not None: 
                        onchange=(onchange, weakref.ref(self))
                    valuefrom=arg.getProperty("valuefrom")
                    if valuefrom is not None: 
                        valuefrom=(valuefrom, weakref.ref(self))
                                     
                    try:
                        comboitems=arg["type"]["item"]
                    except IndexError:
                        try:
                            newCommand.addArgument(arg.getProperty('name'), arg.type, onchange=onchange, valuefrom=valuefrom)
                        except AttributeError:
                            logging.getLogger().error('%s, command "%s": could not add argument %d, missing type or name', self.name(), cmdName, i)
                            continue
                    else:
                        if type(comboitems) == types.ListType:
                            combo_items = []
                            for item in comboitems:
                                name = item.getProperty('name')
                                value = item.getProperty('value')
                                if name is None or value is None:
                                    logging.getLogger().error("%s, command '%s': could not add argument %d, missing combo item name or value", self.name(), cmdName, i)
                                    continue
                                else:
                                    combo_items.append( (name, value) )
                        else:
                            name = comboitems.getProperty('name')
                            value = comboitems.getProperty('value')
                            if name is None or value is None:
                                combo_items = ( (name, value), )
                            else:
                                logging.getLogger().error("%s, command '%s': could not add argument %d, missing combo item name or value", self.name(), cmdName, i)
                                continue
                            
                        newCommand.addArgument(arg.getProperty('name'), "combo", combo_items, onchange, valuefrom)
                    
                    i += 1                               
                    
            return newCommand


    def _addChannelsAndCommands(self):
        [ self.addChannel(*args) for args in self.__channelsToAdd]
        [ self.addCommand(*args) for args in self.__commandsToAdd]
        self.__channelsToAdd = []
        self.__commandsToAdd = []

        
    def executeCommand(self, cmdName, *args, **kwargs):
        if cmdName in self.__commands:
            return self.__commands[cmdName](*args, **kwargs)
        else:
            raise AttributeError


