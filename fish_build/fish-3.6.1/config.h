/* Define to 1 if you have the `backtrace_symbols' function. */
#define HAVE_BACKTRACE_SYMBOLS 1

/* Define to 1 if compiled on WSL */
/* #undef WSL */

/* Define to 1 if you have the `ctermid_r' function. */
#define HAVE_CTERMID_R 1

/* Define to 1 if C++11 thread_local is supported. */
#define HAVE_CX11_THREAD_LOCAL 1

/* Define to 1 if you have the `dirfd' function. */
#define HAVE_DIRFD 1

/* Define to 1 if you have the <execinfo.h> header file. */
#define HAVE_EXECINFO_H 1

/* Define to 1 if you have the `flock' function. */
#define HAVE_FLOCK 1

/* Define to 1 if you have the `getpwent' function. */
#define HAVE_GETPWENT 1

/* Define to 1 if you have the 'getrusage' function. */
#define HAVE_GETRUSAGE 1

/* Define to 1 if you have the `gettext' function. */
#define HAVE_GETTEXT 1

/* Define to 1 if you have the `killpg' function. */
#define HAVE_KILLPG 1

/* Define to 1 if you have the `mkostemp' function. */
/* #undef HAVE_MKOSTEMP */

/* Define to 1 if you have the <curses.h> header file. */
#define HAVE_CURSES_H 1

/* Define to 1 if you have the <ncurses/curses.h> header file. */
/* #undef HAVE_NCURSES_CURSES_H */

/* Define to 1 if you have the <ncurses.h> header file. */
#define HAVE_NCURSES_H 1

/* Define to 1 if you have the <ncurses/term.h> header file. */
/* #undef HAVE_NCURSES_TERM_H */

/* Define to 1 if you have the 'eventfd' function. */
/* #undef HAVE_EVENTFD */

/* Define to 1 if you have the 'pipe2' function. */
/* #undef HAVE_PIPE2 */

/* Define to 1 if you have the <siginfo.h> header file. */
/* #undef HAVE_SIGINFO_H */

/* Define to 1 if you have the <spawn.h> header file. */
#define HAVE_SPAWN_H 1

/* Define to 1 if you have the `std::wcscasecmp' function. */
/* #undef HAVE_STD__WCSCASECMP */

/* Define to 1 if you have the `std::wcsncasecmp' function. */
/* #undef HAVE_STD__WCSNCASECMP */

/* Define to 1 if `d_type' is a member of `struct dirent'. */
#define HAVE_STRUCT_DIRENT_D_TYPE 1

/* Define to 1 if `st_ctime_nsec' is a member of `struct stat'. */
/* #undef HAVE_STRUCT_STAT_ST_CTIME_NSEC */

/* Define to 1 if `st_mtimespec.tv_nsec' is a member of `struct stat'. */
#define HAVE_STRUCT_STAT_ST_MTIMESPEC_TV_NSEC 1

/* Define to 1 if `st_mtim.tv_nsec' is a member of `struct stat'. */
/* #undef HAVE_STRUCT_STAT_ST_MTIM_TV_NSEC */

/* Define to 1 if you have the <sys/ioctl.h> header file. */
#define HAVE_SYS_IOCTL_H 1

/* Define to 1 if you have the <sys/select.h> header file. */
#define HAVE_SYS_SELECT_H 1

/* Define to 1 if you have the <sys/sysctl.h> header file. */
#define HAVE_SYS_SYSCTL_H 1

/* Define to 1 if you have the <term.h> header file. */
#define HAVE_TERM_H 1

/* Define to 1 if you have the `wcscasecmp' function. */
#define HAVE_WCSCASECMP 1

/* Define to 1 if you have the `wcsncasecmp' function. */
#define HAVE_WCSNCASECMP 1

/* Define to 1 if you have the `wcstod_l' function. */
#define HAVE_WCSTOD_L 1

/* Define to 1 if the status that wait returns and WEXITSTATUS expects is signal and then ret instead of the other way around. */
/* #undef HAVE_WAITSTATUS_SIGNAL_RET */

/* Define to 1 if the winsize struct and TIOCGWINSZ macro exist */
#define HAVE_WINSIZE 1

/* Define to 1 if the _nl_msg_cat_cntr symbol is exported. */
#define HAVE__NL_MSG_CAT_CNTR 1

/* Define to 1 if std::make_unique is available. */
/* #undef HAVE_STD__MAKE_UNIQUE */

/* Define to use clock_gettime and futimens to hack around Linux mtime issue */
/* #undef UVAR_FILE_SET_MTIME_HACK */

/* Define to 1 to disable ncurses macros that conflict with the STL */
#define NCURSES_NOMACROS 1

/* Define to 1 to disable curses macros that conflict with the STL */
#define NOMACROS 1

/* Define to the address where bug reports for this package should be sent. */
#define PACKAGE_BUGREPORT "https://github.com/fish-shell/fish-shell/issues"

/* Define to the full name of this package. */
#define PACKAGE_NAME "fish"

/* Use a variadic tparm on NetBSD curses. */
#define TPARM_VARARGS 1

/* The parameter type for the last tputs parameter */
#define TPUTS_USES_INT_ARG 1

/* Define to 1 if tparm accepts a fixed amount of parameters. */
/* #undef TPARM_SOLARIS_KLUDGE */

/* Enable GNU extensions on systems that have them.  */
#ifndef _GNU_SOURCE
# define _GNU_SOURCE 1
#endif

/* The size of wchar_t in bits. */
#define WCHAR_T_BITS 32

/* Define if xlocale.h is required for locale_t or wide character support */
#define HAVE_XLOCALE_H 1

/* Define if uselocale is available */
#define HAVE_USELOCALE 1

/* Enable large inode numbers on Mac OS X 10.5.  */
#ifndef _DARWIN_USE_64_BIT_INODE
# define _DARWIN_USE_64_BIT_INODE 1
#endif

/* Define to 1 if mbrtowc attempts to convert invalid UTF-8 sequences */
#define HAVE_BROKEN_MBRTOWC_UTF8 1

/* Support __warn_unused on function return values. */
#if __GNUC__ >= 3
#ifndef __warn_unused
#define __warn_unused __attribute__ ((warn_unused_result))
#endif
#else
#define __warn_unused
#endif

/* Like __warn_unused, but applies to a type.
   At the moment only clang supports this as a type attribute.

   We need to check for __has_attribute being a thing before or old gcc fails - #7554.
*/
#ifndef __has_attribute
  #define __has_attribute(x) 0  // Compatibility with non-clang and old gcc compilers.
#endif

#if defined(__clang__) && __has_attribute(warn_unused_result)
#ifndef __warn_unused_type
#define __warn_unused_type __attribute__ ((warn_unused_result))
#endif
#else
#define __warn_unused_type
#endif

#if __has_attribute(fallthrough)
#define __fallthrough__ __attribute__ ((fallthrough));
#else
#define __fallthrough__
#endif
