using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Net.Sockets;
using System.Text;

namespace DsCheatEngineServer
{
    class Program
    {
        static void Main(string[] args)
        {
            SocketClient cheatEngineSocketClient = new SocketClient(31000);
            Dictionary<string, long[]> cheatEngineAddressDictionary = updateCheatEngineDictionary(cheatEngineSocketClient);
            var serverSocket = SocketServer.getListeningServerSocket(31001);

            while (true)
            {
                Console.WriteLine("Waiting for connection...");
                try
                {
                    Socket handler = serverSocket.Accept();
                    string data = null;
                    // An incoming connection needs to be processed.  
                    while (true)
                    {
                        byte[] bytes = new byte[1024];
                        int bytesRec = handler.Receive(bytes);
                        data += Encoding.UTF8.GetString(bytes, 0, bytesRec);
                        if (data.IndexOf("\n") > -1)
                        {
                            break;
                        }
                    }

                    // Show the data on the console.  
                    Console.WriteLine("Text received : {0}", data);

                    if (data.IndexOf("updateAddress") > -1)
                    {
                        cheatEngineSocketClient = new SocketClient(31000);
                        cheatEngineAddressDictionary = updateCheatEngineDictionary(cheatEngineSocketClient);
                    }
                    else
                    {
                        // Send state back to client 
                        byte[] msg = Encoding.UTF8.GetBytes(getDsState(cheatEngineAddressDictionary));

                        handler.Send(msg);
                        
                    }
                    handler.Shutdown(SocketShutdown.Both);
                    handler.Close();

                }
                catch (Exception e)
                {
                    Console.WriteLine(e.ToString());
                }
            }
        }

        private static string getDsState(Dictionary<string, long[]> cheatEngineAddressDictionary)
        {
            Process process = Process.GetProcessesByName("eldenring")[0];
            ProcessMemory pm = ProcessMemory.ForProcess(process);


            string state = getStateFromDict(cheatEngineAddressDictionary, pm);
            Console.WriteLine("Read this:");
            Console.WriteLine(state);
            return state;
        }

        private static Dictionary<string, long[]> updateCheatEngineDictionary(SocketClient cheatEngineSocketClient)
        {
            var strToParse = cheatEngineSocketClient.SendAndReceive("getAddr \n");
            var cheatEngineAddressDictionary = parseCeString(strToParse);
            return cheatEngineAddressDictionary;
        }

        private static string getStateFromDict(Dictionary<string, long[]> dict, ProcessMemory pm)
        {
            var state = "";
            for (int i = 0; i < dict.Count; i++)
            {
                var item = dict.ElementAt(i);
                pm.Address = item.Value[0];
                long type = item.Value[1];
                switch (type)
                {
                    case 0:
                        state += item.Key + "::" + pm.AsByte() + ";;";
                        break;
                    case 2:
                        state += item.Key + "::" + BitConverter.ToInt32(pm.AsBytes(4)) + ";;";
                        break;
                    case 4:
                        state += item.Key + "::" + BitConverter.ToSingle(pm.AsBytes(4)) + ";;";
                        break;
                    case 6:
                        state += item.Key + "::" + pm.AsString((int)item.Value[2], System.Text.Encoding.Unicode) + ";;";
                        break;
                    default:
                        state += item.Key + ":: default" + ";;";
                        break;
                }


            }
            //Remove last ;;
            state = state.Substring(0,state.Length - 2);

            return state;
        }

        public static Dictionary<string,long[]> parseCeString(string ceString)
        {
            var dict = new Dictionary<string, long[]>();

            var entries = ceString.Split(";;");
            for (int i = 0; i < entries.Length; i++)
            {
                var entrySplit = entries[i].Split("::");
                dict.Add(entrySplit[0], new long[] { long.Parse(entrySplit[1]), long.Parse(entrySplit[2]), long.Parse(entrySplit[3]) });
            }

            return dict;
        }
    }
}
