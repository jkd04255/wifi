// Small native Windows launcher. Embeds the single-file HTML as a Win32 resource.
// Requires neither Python nor Node nor a separate HTML download at runtime.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <string>
#include <algorithm>
#pragma comment(lib,"shell32.lib")
static std::wstring env(const wchar_t* key) {
    wchar_t buf[32768]={};
    DWORD n=GetEnvironmentVariableW(key,buf,32768);
    return n>0&&n<32768?std::wstring(buf,n):L"";
}
static bool exists(const std::wstring& p) {
    DWORD a=GetFileAttributesW(p.c_str());
    return a!=INVALID_FILE_ATTRIBUTES && !(a&FILE_ATTRIBUTE_DIRECTORY);
}
static bool launchEdge(const std::wstring& url) {
    std::wstring locations[]={
        env(L"ProgramFiles(x86)")+L"\\Microsoft\\Edge\\Application\\msedge.exe",
        env(L"ProgramFiles")+L"\\Microsoft\\Edge\\Application\\msedge.exe",
        env(L"LOCALAPPDATA")+L"\\Microsoft\\Edge\\Application\\msedge.exe"
    };
    for(const auto& exe:locations){
        if(!exists(exe))continue;
        std::wstring args=L"\""+exe+L"\" --app=\""+url+L"\" --no-first-run";
        STARTUPINFOW si={};si.cb=sizeof(si);
        PROCESS_INFORMATION pi={};
        // CreateProcessW needs mutable command-line storage.
        if(CreateProcessW(exe.c_str(),args.data(),nullptr,nullptr,FALSE,0,nullptr,nullptr,&si,&pi)){
            CloseHandle(pi.hThread);CloseHandle(pi.hProcess);return true;
        }
    }
    return false;
}
int WINAPI wWinMain(HINSTANCE inst,HINSTANCE,LPWSTR,int) {
    HRSRC r=FindResourceW(inst,MAKEINTRESOURCEW(101),RT_RCDATA);
    if(!r)return 2;
    HGLOBAL blob=LoadResource(inst,r);
    if(!blob)return 3;
    const void* data=LockResource(blob);DWORD size=SizeofResource(inst,r);
    if(!data||size<1000)return 4;
    std::wstring base=env(L"LOCALAPPDATA");
    if(base.empty())base=env(L"TEMP");
    if(base.empty())return 5;
    std::wstring directory=base+L"\\WiFiPlacementStudio";
    CreateDirectoryW(directory.c_str(),nullptr);
    std::wstring path=directory+L"\\studio_offline.html";
    HANDLE file=CreateFileW(path.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return 6;
    DWORD written=0;BOOL ok=WriteFile(file,data,size,&written,nullptr);
    CloseHandle(file);
    if(!ok||written!=size)return 7;
    std::wstring url=L"file:///"+path;
    std::replace(url.begin(),url.end(),L'\\',L'/');
    if(launchEdge(url))return 0;
    HINSTANCE opened=ShellExecuteW(nullptr,L"open",path.c_str(),nullptr,nullptr,SW_SHOWNORMAL);
    if(reinterpret_cast<INT_PTR>(opened)>32)return 0;
    MessageBoxW(nullptr,L"HTML을 열 브라우저를 찾지 못했습니다.",L"Wi-Fi Placement Studio",MB_OK|MB_ICONERROR);
    return 8;
}
