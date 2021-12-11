using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;

namespace DsCheatEngineServer
{
    class SocketClient
    {
        public Socket Sender { get; set; }
        public IPEndPoint RemoteEP { get; set; }
        public SocketClient(int port)
        {
            

            try
            {
                // Connect to a Remote server
                // Get Host IP Address that is used to establish a connection
                // In this case, we get one IP address of localhost that is IP : 127.0.0.1
                // If a host has multiple addresses, you will get a list of addresses
                IPHostEntry host = Dns.GetHostEntry("127.0.0.1");
                IPAddress ipAddress = host.AddressList[1];
                RemoteEP = new IPEndPoint(ipAddress, port);

                // Create a TCP/IP  socket.

                Sender = new Socket(ipAddress.AddressFamily,
                    SocketType.Stream, ProtocolType.Tcp);

            }
            catch (Exception e)
            {
                Console.WriteLine(e.ToString());
            }
        }
        public string SendAndReceive(string toSend)
        {
            byte[] bytes = new byte[1024];
            // Connect the socket to the remote endpoint. Catch any errors.
            try
            {
                // Connect to Remote EndPoint
                Sender.Connect(RemoteEP);

                Console.WriteLine("Socket connected to {0}",
                    Sender.RemoteEndPoint.ToString());

                // Encode the data string into a byte array.
                byte[] msg = Encoding.UTF8.GetBytes(toSend);

                // Send the data through the socket.
                int bytesSent = Sender.Send(msg);
                Console.WriteLine("bytes sent" + bytesSent);
                // Receive the response from the remote device.
                int bytesRec = Sender.Receive(bytes);
                string received = Encoding.UTF8.GetString(bytes, 0, bytesRec);
                Console.WriteLine("Echoed test = {0}", received
                    );

                // Release the socket.
                Sender.Shutdown(SocketShutdown.Both);
                Sender.Close();
                return received;

            }
            catch (ArgumentNullException ane)
            {
                Console.WriteLine("ArgumentNullException : {0}", ane.ToString());
            }
            catch (SocketException se)
            {
                Console.WriteLine("SocketException : {0}", se.ToString());
            }
            catch (Exception e)
            {
                Console.WriteLine("Unexpected exception : {0}", e.ToString());
            }
            return String.Empty;
        }
    }
}
