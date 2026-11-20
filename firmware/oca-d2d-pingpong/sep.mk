# SPDX-License-Identifier: Apache-2.0
SEPT   = $(abspath $(MODEL_ROOT))/sw/sep-vp-tests
SRCS   = $(SEPT)/common/start.S sep_main.c $(SEPT)/common/printf.c
OBJS   = $(SRCS:.c=.o)
OBJS  := $(OBJS:.S=.o)
TARGET = oca_d2d_sep
LDFLAGS += -T $(SEPT)/common/link.ld
include $(SEPT)/Makefile.common
