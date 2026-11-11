#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shlwapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#pragma comment(lib,"shlwapi.lib")
#pragma comment(lib,"advapi32.lib")

/* Native Win32 launcher: embeds ONE fully-offline HTML file. No Python,
 * FastAPI, WebView2 .NET bridge, server, port or LAN/cable constraints. */
#define HTML_RESOURCE_ID 101
#define WINDOW_TITLE L"Wi-Fi Placement Studio - Required Area 70 / No LAN"
#define MAX_TEXT 4096

static void error_box(const wchar_t *message) {
    MessageBoxW(NULL, message, WINDOW_TITLE, MB_OK | MB_ICONERROR);
}
static int browser_exists(const wchar_t *parent,const wchar_t *rel,wchar_t *out,DWORD count) {
    if (!parent || !*parent) return 0;
    if (swprintf_s(out,count,L"%ls\\%ls",parent,rel)<0) return 0;
    DWORD attrs=GetFileAttributesW(out);
    return attrs!=INVALID_FILE_ATTRIBUTES && !(attrs&FILE_ATTRIBUTE_DIRECTORY);
}
static int find_browser(wchar_t *output,DWORD length) {
    wchar_t base[MAX_PATH];
    const wchar_t *envs[]={L"PROGRAMFILES(X86)",L"PROGRAMFILES",L"LOCALAPPDATA"};
    const wchar_t *rel[]={L"Microsoft\\Edge\\Application\\msedge.exe",
                         L"Google\\Chrome\\Application\\chrome.exe"};
    for(int i=0;i<3;i++){
        DWORD n=GetEnvironmentVariableW(envs[i],base,MAX_PATH);
        if(!n||n>=MAX_PATH)continue;
        for(int j=0;j<2;j++)
            if(browser_exists(base,rel[j],output,length))return 1;
    }
    const wchar_t *names[]={L"msedge.exe",L"chrome.exe"};
    HKEY keys[]={HKEY_CURRENT_USER,HKEY_LOCAL_MACHINE};
    for(int i=0;i<2;i++)for(int j=0;j<2;j++){
        wchar_t reg[MAX_PATH];
        if(swprintf_s(reg,MAX_PATH,
            L"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\%ls",
            names[j])<0)continue;
        DWORD bytes=length*sizeof(wchar_t);
        if(RegGetValueW(keys[i],reg,NULL,RRF_RT_REG_SZ,NULL,output,&bytes)==ERROR_SUCCESS){
            DWORD attrs=GetFileAttributesW(output);
            if(attrs!=INVALID_FILE_ATTRIBUTES && !(attrs&FILE_ATTRIBUTE_DIRECTORY))return 1;
        }
    }
    return 0;
}
static int has_text(const char *buffer,const char *needle) {
    return strstr(buffer,needle)!=NULL;
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE old,LPWSTR cmdline,int show){
    (void)instance;(void)old;(void)show;
    HRSRC res=FindResourceW(NULL,MAKEINTRESOURCEW(HTML_RESOURCE_ID),RT_RCDATA);
    if(!res){error_box(L"HTML resource missing");return 2;}
    DWORD length=SizeofResource(NULL,res);
    HGLOBAL loaded=LoadResource(NULL,res);
    if(!loaded || length<80000){error_box(L"Invalid HTML resource");return 3;}
    const BYTE *bytes=(const BYTE *)LockResource(loaded);
    if(!bytes){error_box(L"Unable to read HTML resource");return 4;}
    char *check=(char *)malloc((size_t)length+1);
    if(!check){error_box(L"Out of memory");return 5;}
    memcpy(check,bytes,length);check[length]=0;
    int valid=has_text(check,"data-tool=\"required\"")
      && has_text(check,"id=\"requiredPinSelect\"")
      && has_text(check,"function requiredSamples")
      && has_text(check,"requiredAreaSatisfied")
      && !has_text(check,"data-tool=\"zone\"")
      && !has_text(check,"id=\"roomDrawer\"")
      && !has_text(check,"id=\"requiredRadius\"")
      && !has_text(check,"id=\"selectedRequiredRadius\"")
      && !has_text(check,"id=\"g3LanX\"")
      && !has_text(check,"id=\"g3Cable\"");
    free(check);
    if(!valid){error_box(L"Missing mandatory-pin / no-LAN features");return 6;}
    if(wcsstr(cmdline,L"--self-test"))return 0;

    wchar_t root[MAX_PATH],folder[MAX_PATH],html[MAX_PATH];
    DWORD n=GetEnvironmentVariableW(L"LOCALAPPDATA",root,MAX_PATH);
    if(n==0||n>=MAX_PATH){error_box(L"Cannot locate LOCALAPPDATA");return 7;}
    if(swprintf_s(folder,MAX_PATH,L"%ls\\WiFiRequiredPin70",root)<0)return 8;
    if(!CreateDirectoryW(folder,NULL)&&GetLastError()!=ERROR_ALREADY_EXISTS){
        error_box(L"Cannot create local app folder");return 9;
    }
    if(swprintf_s(html,MAX_PATH,L"%ls\\app.html",folder)<0)return 10;
    HANDLE target=CreateFileW(html,GENERIC_WRITE,FILE_SHARE_READ,NULL,
                               CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(target==INVALID_HANDLE_VALUE){error_box(L"Cannot extract HTML");return 11;}
    DWORD written=0;BOOL ok=WriteFile(target,bytes,length,&written,NULL);
    CloseHandle(target);
    if(!ok||written!=length){error_box(L"Failed to write HTML file");return 12;}

    wchar_t browser[MAX_PATH];
    if(!find_browser(browser,MAX_PATH)){
        error_box(L"Microsoft Edge or Google Chrome is required.");return 13;
    }
    wchar_t url[MAX_TEXT];
    DWORD urlLen=MAX_TEXT;
    HRESULT hr=UrlCreateFromPathW(html,url,&urlLen,0);
    if(FAILED(hr)){error_box(L"Cannot build file URL");return 14;}
    wchar_t command[MAX_TEXT+2*MAX_PATH+200];
    if(swprintf_s(command,_countof(command),
        L"\"%ls\" --app=\"%ls\" --no-first-run --window-size=1440,900",
        browser,url)<0)return 15;
    STARTUPINFOW si={0};si.cb=sizeof(si);
    PROCESS_INFORMATION pi={0};
    if(!CreateProcessW(browser,command,NULL,NULL,FALSE,0,NULL,NULL,&si,&pi)){
        error_box(L"Unable to open app window");return 16;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}
