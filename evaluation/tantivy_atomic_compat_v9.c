/* Process-local, import-table scoped compatibility for Tantivy 0.27.0.
 * No deletion, copy fallback, writer retry, or change to index format.
 * Only .tmp* -> .managed.json in the configured directory, flags==REPLACE_EXISTING.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <wchar.h>
#include <string.h>

typedef BOOL (WINAPI *move_fn)(LPCWSTR,LPCWSTR,DWORD);
static move_fn real_move;
static WCHAR root[32768], stop_path[32768], log_path[32768];
static double deadline;
static volatile LONG installed, cancelled, calls, failures, recovered, exhausted, log_failed;
static CRITICAL_SECTION log_lock;
static DWORD waits[]={10,20,40,80,160,320,640};

static double now(void){FILETIME f; ULARGE_INTEGER u; GetSystemTimeAsFileTime(&f);u.LowPart=f.dwLowDateTime;u.HighPart=f.dwHighDateTime;return u.QuadPart/10000000.0-11644473600.0;}
static DWORD admission(void){if(InterlockedCompareExchange(&cancelled,0,0))return ERROR_OPERATION_ABORTED;if(now()>=deadline)return ERROR_TIMEOUT;if(stop_path[0]&&GetFileAttributesW(stop_path)!=INVALID_FILE_ATTRIBUTES)return ERROR_OPERATION_ABORTED;if(log_failed)return ERROR_WRITE_FAULT;return 0;}
static void record(const char *kind,DWORD error,DWORD attempt,ULONGLONG start,LPCWSTR src,LPCWSTR dst){
    DWORD saved=GetLastError();char a[32768],b[32768],line[68000];
    WideCharToMultiByte(CP_UTF8,0,src,-1,a,sizeof(a),NULL,NULL);WideCharToMultiByte(CP_UTF8,0,dst,-1,b,sizeof(b),NULL,NULL);
    /* JSON escape only the paths: Windows names cannot contain quotes/control
       characters in this narrowly admitted index directory. Backslash doubles. */
    char ea[65536],eb[65536];size_t j=0;for(size_t i=0;a[i]&&j<sizeof(ea)-3;i++){if(a[i]=='\\')ea[j++]='\\';ea[j++]=a[i];}ea[j]=0;
    j=0;for(size_t i=0;b[i]&&j<sizeof(eb)-3;i++){if(b[i]=='\\')eb[j++]='\\';eb[j++]=b[i];}eb[j]=0;
    int n=snprintf(line,sizeof(line),"{\"kind\":\"%s\",\"wall\":%.6f,\"pid\":%lu,\"thread\":%lu,\"error\":%lu,\"attempt\":%lu,\"elapsed_ms\":%llu,\"source\":\"%s\",\"target\":\"%s\"}\n",kind,now(),GetCurrentProcessId(),GetCurrentThreadId(),error,attempt,GetTickCount64()-start,ea,eb);
    EnterCriticalSection(&log_lock);HANDLE f=CreateFileW(log_path,FILE_APPEND_DATA,FILE_SHARE_READ,NULL,OPEN_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);DWORD written=0;LARGE_INTEGER size;
    if(f==INVALID_HANDLE_VALUE||!GetFileSizeEx(f,&size)||size.QuadPart+n>32*1024*1024||n<=0||n>=sizeof(line)||!WriteFile(f,line,n,&written,NULL)||written!=(DWORD)n||!FlushFileBuffers(f))InterlockedExchange(&log_failed,1);
    if(f!=INVALID_HANDLE_VALUE)CloseHandle(f);LeaveCriticalSection(&log_lock);SetLastError(saved);
}
static LPCWSTR normalized(LPCWSTR p){return wcsncmp(p,L"\\\\?\\",4)==0?p+4:p;}
static BOOL scope(LPCWSTR src,LPCWSTR dst,DWORD flags){
    if(!src||!dst||flags!=MOVEFILE_REPLACE_EXISTING)return FALSE;
    src=normalized(src);dst=normalized(dst);size_t n=wcslen(root);
    return _wcsnicmp(src,root,n)==0&&_wcsnicmp(dst,root,n)==0&&
        _wcsicmp(dst+n,L"\\.managed.json")==0&&wcsncmp(src+n,L"\\.tmp",5)==0&&wcschr(src+n+1,L'\\')==NULL;
}
static BOOL snapshot(LPCWSTR path,BY_HANDLE_FILE_INFORMATION *info,DWORD *error){
    HANDLE h=CreateFileW(path,FILE_READ_ATTRIBUTES,7,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
    if(h==INVALID_HANDLE_VALUE){*error=GetLastError();return FALSE;}BOOL ok=GetFileInformationByHandle(h,info);*error=ok?0:GetLastError();CloseHandle(h);
    if(ok&&(info->dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_READONLY|FILE_ATTRIBUTE_REPARSE_POINT))){*error=ERROR_ACCESS_DENIED;return FALSE;}return ok;
}
static BOOL same(BY_HANDLE_FILE_INFORMATION *a,BY_HANDLE_FILE_INFORMATION *b){
    return a->dwVolumeSerialNumber==b->dwVolumeSerialNumber&&a->nFileIndexHigh==b->nFileIndexHigh&&a->nFileIndexLow==b->nFileIndexLow&&a->nFileSizeHigh==b->nFileSizeHigh&&a->nFileSizeLow==b->nFileSizeLow&&CompareFileTime(&a->ftLastWriteTime,&b->ftLastWriteTime)==0&&a->dwFileAttributes==b->dwFileAttributes;
}
static BOOL deletable(LPCWSTR path){HANDLE h=CreateFileW(path,DELETE|FILE_READ_ATTRIBUTES,7,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);if(h==INVALID_HANDLE_VALUE)return GetLastError()==ERROR_SHARING_VIOLATION;CloseHandle(h);return TRUE;}
static BOOL WINAPI compatible_move(LPCWSTR src,LPCWSTR dst,DWORD flags){
    if(!scope(src,dst,flags))return real_move(src,dst,flags);
    InterlockedIncrement(&calls);DWORD why=admission();ULONGLONG start=GetTickCount64();
    if(why){record("admission_stopped",why,0,start,src,dst);SetLastError(why);return FALSE;}
    BY_HANDLE_FILE_INFORMATION before_src,before_dst,after_src,after_dst;DWORD se=0,de=0;
    BOOL stable=snapshot(src,&before_src,&se)&&snapshot(dst,&before_dst,&de);
    if(real_move(src,dst,flags))return TRUE;
    DWORD original=GetLastError(),last=original;InterlockedIncrement(&failures);record("replace_failed",last,1,start,src,dst);
    /* Error 5 is not labelled transient. Retry only if both exact files survive,
       are regular/writable and DELETE access is allowed (or sharing prevents it).
       A missing target (first creation), readonly/path/ACL failure is never retried. */
    if(!stable||(last!=ERROR_ACCESS_DENIED&&last!=ERROR_SHARING_VIOLATION&&last!=ERROR_LOCK_VIOLATION))goto fail;
    for(DWORD i=0;i<sizeof(waits)/sizeof(waits[0]);i++){
        if(!snapshot(src,&after_src,&se)||!snapshot(dst,&after_dst,&de)||!same(&before_src,&after_src)||!same(&before_dst,&after_dst)||!deletable(src)||!deletable(dst)){record("state_or_access_rejected",last,i+1,start,src,dst);goto fail;}
        DWORD remaining=waits[i];while(remaining){why=admission();if(why){last=why;record("retry_stopped",last,i+1,start,src,dst);goto fail;}DWORD slice=remaining>10?10:remaining;Sleep(slice);remaining-=slice;}
        why=admission();if(why){last=why;goto fail;}
        if(GetTickCount64()-start>=2000){last=original;goto fail;}
        /* Revalidate after waiting: never overwrite an unexpected new target. */
        if(!snapshot(src,&after_src,&se)||!snapshot(dst,&after_dst,&de)||!same(&before_src,&after_src)||!same(&before_dst,&after_dst)){record("state_changed",last,i+1,start,src,dst);goto fail;}
        if(real_move(src,dst,flags)){InterlockedIncrement(&recovered);record("replace_recovered",0,i+2,start,src,dst);return TRUE;}
        last=GetLastError();record("replace_failed",last,i+2,start,src,dst);
        if(last!=ERROR_ACCESS_DENIED&&last!=ERROR_SHARING_VIOLATION&&last!=ERROR_LOCK_VIOLATION)goto fail;
    }
    InterlockedIncrement(&exhausted);record("retry_exhausted",last,8,start,src,dst);
fail:SetLastError(last);return FALSE;
}
__declspec(dllexport) DWORD WINAPI ptai_install(HMODULE module,LPCWSTR directory,LPCWSTR stop,LPCWSTR log,double until){
    if(InterlockedCompareExchange(&installed,1,0))return ERROR_ALREADY_EXISTS;
    if(!module||wcslen(normalized(directory))>=32760||wcslen(stop)>=32760||wcslen(log)>=32760)return ERROR_INVALID_PARAMETER;
    wcscpy(root,normalized(directory));wcscpy(stop_path,stop);wcscpy(log_path,log);deadline=until;InitializeCriticalSection(&log_lock);
    BYTE *base=(BYTE*)module;IMAGE_DOS_HEADER *dos=(void*)base;IMAGE_NT_HEADERS64 *nt=(void*)(base+dos->e_lfanew);
    if(dos->e_magic!=IMAGE_DOS_SIGNATURE||nt->Signature!=IMAGE_NT_SIGNATURE||nt->OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC)return ERROR_BAD_EXE_FORMAT;
    IMAGE_IMPORT_DESCRIPTOR *desc=(void*)(base+nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress);
    for(;desc->Name;desc++){
        if(!desc->OriginalFirstThunk)continue;
        IMAGE_THUNK_DATA64 *names=(void*)(base+desc->OriginalFirstThunk),*iat=(void*)(base+desc->FirstThunk);
        for(;names->u1.AddressOfData;names++,iat++){
            if(IMAGE_SNAP_BY_ORDINAL64(names->u1.Ordinal))continue;
            IMAGE_IMPORT_BY_NAME *name=(void*)(base+names->u1.AddressOfData);
            if(strcmp((char*)name->Name,"MoveFileExW"))continue;
            DWORD protection;real_move=(move_fn)(uintptr_t)iat->u1.Function;
            if(!VirtualProtect(&iat->u1.Function,sizeof(void*),PAGE_READWRITE,&protection))return GetLastError();
            InterlockedExchangePointer((void**)&iat->u1.Function,(void*)compatible_move);
            DWORD ignored;if(!VirtualProtect(&iat->u1.Function,sizeof(void*),protection,&ignored))return GetLastError();
            return 0;
        }
    }
    return ERROR_PROC_NOT_FOUND;
}
/* Test export executes precisely the same native implementation, no Python callback/GIL. */
__declspec(dllexport) BOOL WINAPI ptai_test_replace(LPCWSTR a,LPCWSTR b,DWORD f){return compatible_move(a,b,f);}
__declspec(dllexport) void WINAPI ptai_cancel(void){InterlockedExchange(&cancelled,1);}
__declspec(dllexport) void WINAPI ptai_stats(LONG *out){out[0]=calls;out[1]=failures;out[2]=recovered;out[3]=exhausted;out[4]=log_failed;}
