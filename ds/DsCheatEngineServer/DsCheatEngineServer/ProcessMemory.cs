using System;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;

public struct ProcessMemory
{
    #region Constructors

    private ProcessMemory(Process process, long address) : this()
    {
        Process = process;
        Address = address;
    }

    private ProcessMemory(Process process) : this()
    {
        Process = process;
    }

    #endregion

    #region Factories

    public static ProcessMemory ForProcess(Process process)
    {
        if (process == null)
            throw new ArgumentNullException("process");

        return new ProcessMemory(process);
    }

    #endregion

    #region Properties

    public long Address { get; set; }

    public Process Process { get; private set; }

    public ProcessMemory this[int offset]
    {
        get { return AtOffset(offset); }
    }

    public ProcessMemory this[string module]
    {
        get { return GetModule(module); }
    }

    #endregion

    #region Reading methods

    public ProcessMemory AsPointer()
    {
        return new ProcessMemory(Process, AsInteger());
    }

    public int AsInteger()
    {
        if (Process.HasExited)
            throw new InvalidOperationException("The process has exited.");

        return BitConverter.ToInt32(Read(Process, Address, 4), 0);
    }

    public float AsFloat()
    {
        if (Process.HasExited)
            throw new InvalidOperationException("The process has exited.");

        return BitConverter.ToSingle(Read(Process, Address, 4), 0);
    }

    public byte AsByte()
    {
        if (Process.HasExited)
            throw new InvalidOperationException("The process has exited.");

        return Read(Process, Address, 1)[0];
    }

    public byte[] AsBytes(int count)
    {
        if (Process.HasExited)
            throw new InvalidOperationException("The process has exited.");

        return Read(Process, Address, count);
    }

    public short AsShort()
    {
        if (Process.HasExited)
            throw new InvalidOperationException("The process has exited.");

        return BitConverter.ToInt16(Read(Process, Address, 2), 0);
    }

    public string AsString(int length)
    {
        return AsString(length, Encoding.ASCII);
    }

    public string AsString(int length, Encoding encoding)
    {
        if (Process.HasExited)
            throw new InvalidOperationException("The process has exited.");

        var value = Read(Process, Address, length*2);
        if (length == 1)
            return Encoding.ASCII.GetString(value);
        return encoding.GetString(value).Split("\0")[0];
    }


    public void Set(int value)
    {
        Set(BitConverter.GetBytes(value));
    }

    public void Set(float value)
    {
        Debug.WriteLine("Setting {0} to {1}", Address, value);
        Set(BitConverter.GetBytes(value));
    }

    public void Set(byte value)
    {
        Set(BitConverter.GetBytes(value));
    }

    public void Set(byte[] value)
    {
        Write(Process, Address, value);
    }
    public void Set(short value)
    {
        Set(BitConverter.GetBytes(value));
    }

    public void Set(bool value)
    {
        Set(BitConverter.GetBytes(value));
    }

    public void Set(string value, Encoding encoding)
    {
        Set(encoding.GetBytes(value));
    }

    public void Set(string value)
    {
        Set(value, Encoding.ASCII);
    }

    public void Set(string value, Encoding encoding, int length)
    {
        var data = new byte[length];
        var bytes = encoding.GetBytes(value);

        Array.Copy(bytes, data, bytes.Length);

        Set(data);
    }

    public void Set(string value, int length)
    {
        Set(value, Encoding.ASCII, length);
    }

    #endregion

    #region Cast operators

    public static implicit operator int(ProcessMemory memory)
    {
        return memory.AsInteger();
    }

    public static implicit operator short(ProcessMemory memory)
    {
        return memory.AsShort();
    }

    public static implicit operator byte(ProcessMemory memory)
    {
        return memory.AsByte();
    }

    public static implicit operator float(ProcessMemory memory)
    {
        return memory.AsFloat();
    }

    public static implicit operator string(ProcessMemory memory)
    {
        return memory.AsString(256);
    }

    public static implicit operator ProcessMemory(Process process)
    {
        return ForProcess(process);
    }

    #endregion

    #region Operators

    public static ProcessMemory operator ~(ProcessMemory memory)
    {
        return memory.AsPointer();
    }

    public static ProcessMemory operator +(ProcessMemory memory, int offset)
    {
        return memory.AtOffset(offset);
    }

    public static ProcessMemory operator -(ProcessMemory memory, int offset)
    {
        return memory.AtOffset(-offset);
    }

    public static ProcessMemory operator |(ProcessMemory memory, int value)
    {
        memory.Set(value);
        return memory;
    }

    public static ProcessMemory operator |(ProcessMemory memory, short value)
    {
        memory.Set(value);
        return memory;
    }

    public static ProcessMemory operator |(ProcessMemory memory, byte value)
    {
        memory.Set(value);
        return memory;
    }

    public static ProcessMemory operator |(ProcessMemory memory, byte[] value)
    {
        memory.Set(value);
        return memory;
    }

    public static ProcessMemory operator |(ProcessMemory memory, float value)
    {
        memory.Set(value);
        return memory;
    }

    public static ProcessMemory operator |(ProcessMemory memory, string value)
    {
        memory.Set(value);
        return memory;
    }

    public static bool operator false(ProcessMemory memory)
    {
        return memory.Equals(default(ProcessMemory)) || memory.Process == null || memory.Process.HasExited;
    }

    public static bool operator true(ProcessMemory memory)
    {
        return !memory.Equals(default(ProcessMemory)) && memory.Process != null && !memory.Process.HasExited;
    }

    #endregion

    #region Methods

    public ProcessMemory AtAddress(long address)
    {
        if (Process.HasExited)
            throw new InvalidOperationException("The process has exited.");

        return new ProcessMemory(Process, address);
    }

    public ProcessMemory AtOffset(long offset)
    {
        if (Process.HasExited)
            throw new InvalidOperationException("The process has exited.");

        return new ProcessMemory(Process, Address + offset);
    }

    public ProcessMemory GetModule(string moduleName)
    {
        if (Process.HasExited)
            throw new InvalidOperationException("The process has exited.");

        var process = Process;

        return
            process.Modules.Cast<ProcessModule>()
                .Where(
                    module =>
                        String.Compare(module.ModuleName, moduleName, StringComparison.OrdinalIgnoreCase) == 0)
                .Select(module => new ProcessMemory(process, (int)module.BaseAddress))
                .FirstOrDefault();
    }

    public bool Equals(ProcessMemory other)
    {
        return Address == other.Address && Equals(Process, other.Process);
    }

    public override bool Equals(object obj)
    {
        if (ReferenceEquals(null, obj)) return false;
        return obj is ProcessMemory && Equals((ProcessMemory)obj);
    }

    public override string ToString()
    {
        return string.Format("{0}@{1}", Process.ProcessName, Address);
    }

    #endregion

    #region Private methods

    [DllImport("kernel32.dll")]
    private static extern IntPtr OpenProcess(ProcessAccessFlags dwDesiredAccess,
        [MarshalAs(UnmanagedType.Bool)] bool bInheritHandle, int dwProcessId);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool WriteProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, byte[] lpBuffer,
        uint nSize, out int lpNumberOfBytesWritten);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool ReadProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, [Out] byte[] lpBuffer,
        int dwSize, out int lpNumberOfBytesRead);

    [DllImport("kernel32.dll")]
    private static extern Int32 CloseHandle(IntPtr hProcess);

    private static byte[] Read(Process process, long address, int numOfBytes, out int bytesRead)
    {
        IntPtr hProc = OpenProcess(ProcessAccessFlags.All, false, process.Id);
        byte[] buffer = new byte[numOfBytes];
        ReadProcessMemory(hProc, new IntPtr(address), buffer, numOfBytes, out bytesRead);
        CloseHandle(hProc);
        return buffer;
    }

    private static byte[] Read(Process process, long address, int numOfBytes)
    {
        int bytesRead;
        return Read(process, address, numOfBytes, out bytesRead);
    }

    private static void Write(Process process, long address, byte[] bytes)
    {
        IntPtr hProc = OpenProcess(ProcessAccessFlags.All, false, process.Id);
        int numOfBytes;
        WriteProcessMemory(hProc, new IntPtr(address), bytes, (UInt32)bytes.LongLength, out numOfBytes);
        CloseHandle(hProc);
    }

    #endregion

    #region ProcessAccessFlags

    private enum ProcessAccessFlags : uint
    {
        All = 0x001F0FFF,
        Terminate = 0x00000001,
        CreateThread = 0x00000002,
        VMOperation = 0x00000008,
        VMRead = 0x00000010,
        VMWrite = 0x00000020,
        DupHandle = 0x00000040,
        SetInformation = 0x00000200,
        QueryInformation = 0x00000400,
        Synchronize = 0x00100000
    }

    #endregion
}