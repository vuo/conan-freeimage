#include <stdio.h>
#include <FreeImage.h>

int main()
{
	FreeImage_Initialise(false);
	printf("Successfully initialized FreeImage %s\n", FreeImage_GetVersion());
	FreeImage_DeInitialise();
	return 0;
}
