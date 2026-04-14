#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <wchar.h>
#include <stdlib.h>
#include <string.h>

typedef struct fake_hid_device {
    unsigned long magic;
    unsigned int write_count;
    unsigned int read_count;
} fake_hid_device;

static FILE *g_log_file = NULL;
static CRITICAL_SECTION g_log_lock;
static int g_log_lock_ready = 0;
static wchar_t g_error_buf[256];

static void log_open(void) {
    if (!g_log_file) {
        g_log_file = fopen("hidapi-probe.log", "a");
    }
}

static void log_line(const char *prefix, const unsigned char *buf, size_t len) {
    size_t i;

    if (!g_log_lock_ready) {
        return;
    }

    EnterCriticalSection(&g_log_lock);
    log_open();
    if (!g_log_file) {
        LeaveCriticalSection(&g_log_lock);
        return;
    }

    fprintf(g_log_file, "%s %zu", prefix, len);
    for (i = 0; i < len; ++i) {
        fprintf(g_log_file, " %02x", buf[i]);
    }
    fputc('\n', g_log_file);
    fflush(g_log_file);
    LeaveCriticalSection(&g_log_lock);
}

static void log_text(const char *text) {
    if (!g_log_lock_ready) {
        return;
    }

    EnterCriticalSection(&g_log_lock);
    log_open();
    if (g_log_file) {
        fprintf(g_log_file, "%s\n", text);
        fflush(g_log_file);
    }
    LeaveCriticalSection(&g_log_lock);
}

static void set_error_text(const wchar_t *text) {
    wcsncpy(g_error_buf, text, (sizeof(g_error_buf) / sizeof(g_error_buf[0])) - 1);
    g_error_buf[(sizeof(g_error_buf) / sizeof(g_error_buf[0])) - 1] = L'\0';
}

static int hex_value(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    return -1;
}

static size_t parse_hex_line(const char *line, unsigned char *out, size_t out_cap) {
    size_t count = 0;
    int hi = -1;

    while (*line && *line != '\n' && *line != '\r') {
        int v = hex_value(*line);
        if (v >= 0) {
            if (hi < 0) {
                hi = v;
            } else {
                if (count >= out_cap) {
                    return count;
                }
                out[count++] = (unsigned char)((hi << 4) | v);
                hi = -1;
            }
        }
        ++line;
    }

    return count;
}

static size_t load_scripted_response(unsigned int read_index, unsigned char *out, size_t out_cap) {
    FILE *fp;
    char line[2048];
    unsigned int current = 0;

    fp = fopen("hidapi-probe.responses.txt", "r");
    if (!fp) {
        return 0;
    }

    while (fgets(line, sizeof(line), fp)) {
        char *p = line;
        while (*p == ' ' || *p == '\t') {
            ++p;
        }
        if (*p == '#' || *p == '\n' || *p == '\r' || *p == '\0') {
            continue;
        }
        if (current == read_index) {
            size_t n = parse_hex_line(p, out, out_cap);
            fclose(fp);
            return n;
        }
        ++current;
    }

    fclose(fp);
    return 0;
}

__declspec(dllexport) void *hid_open(unsigned short vendor_id, unsigned short product_id, const wchar_t *serial_number) {
    fake_hid_device *dev = (fake_hid_device *)calloc(1, sizeof(fake_hid_device));
    char msg[256];

    (void)serial_number;
    if (!dev) {
        set_error_text(L"hidapi-probe: allocation failed");
        return NULL;
    }

    dev->magic = 0x48494450UL;
    snprintf(msg, sizeof(msg), "hid_open vid=%04x pid=%04x", vendor_id, product_id);
    log_text(msg);
    set_error_text(L"hidapi-probe: ok");
    return dev;
}

__declspec(dllexport) int hid_write(void *device, const unsigned char *data, size_t length) {
    fake_hid_device *dev = (fake_hid_device *)device;

    if (!dev || dev->magic != 0x48494450UL) {
        set_error_text(L"hidapi-probe: invalid device");
        return -1;
    }

    log_line("hid_write", data, length);
    dev->write_count += 1;
    return (int)length;
}

__declspec(dllexport) int hid_read_timeout(void *device, unsigned char *data, size_t length, int milliseconds) {
    fake_hid_device *dev = (fake_hid_device *)device;
    unsigned char scripted[1024];
    size_t scripted_len;
    char msg[128];

    if (!dev || dev->magic != 0x48494450UL) {
        set_error_text(L"hidapi-probe: invalid device");
        return -1;
    }

    snprintf(msg, sizeof(msg), "hid_read_timeout call=%u len=%zu timeout_ms=%d", dev->read_count, length, milliseconds);
    log_text(msg);

    scripted_len = load_scripted_response(dev->read_count, scripted, sizeof(scripted));
    dev->read_count += 1;
    if (scripted_len == 0) {
        Sleep(milliseconds > 0 && milliseconds < 50 ? milliseconds : 10);
        return 0;
    }

    if (scripted_len > length) {
        scripted_len = length;
    }

    memset(data, 0, length);
    memcpy(data, scripted, scripted_len);
    log_line("hid_read_timeout.response", data, scripted_len);
    return (int)scripted_len;
}

__declspec(dllexport) void hid_close(void *device) {
    fake_hid_device *dev = (fake_hid_device *)device;

    log_text("hid_close");
    if (dev && dev->magic == 0x48494450UL) {
        dev->magic = 0;
        free(dev);
    }
}

__declspec(dllexport) const wchar_t *hid_error(void *device) {
    (void)device;
    return g_error_buf;
}

__declspec(dllexport) int hid_get_serial_number_string(void *device, wchar_t *string, size_t maxlen) {
    const wchar_t probe_serial[] = L"HIDAPI-PROBE";
    size_t copy_len;

    (void)device;
    if (!string || maxlen == 0) {
        return -1;
    }

    copy_len = wcslen(probe_serial);
    if (copy_len >= maxlen) {
        copy_len = maxlen - 1;
    }
    wmemcpy(string, probe_serial, copy_len);
    string[copy_len] = L'\0';
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved) {
    (void)instance;
    (void)reserved;

    if (reason == DLL_PROCESS_ATTACH) {
        InitializeCriticalSection(&g_log_lock);
        g_log_lock_ready = 1;
        set_error_text(L"hidapi-probe: initialized");
        log_text("dll_attach");
    } else if (reason == DLL_PROCESS_DETACH) {
        if (g_log_lock_ready) {
            EnterCriticalSection(&g_log_lock);
            if (g_log_file) {
                fclose(g_log_file);
                g_log_file = NULL;
            }
            LeaveCriticalSection(&g_log_lock);
            DeleteCriticalSection(&g_log_lock);
            g_log_lock_ready = 0;
        }
    }
    return TRUE;
}
